# -*- coding: utf-8 -*-
"""Structured output parsing, validation, and post-processing."""
import json
import re
from typing import Any, Dict, List, Optional

from .taxonomy import Taxonomy

STAR_TO_TYPE = {"差评": (1, 2), "中评": (3, 3), "好评": (4, 5)}


def review_type_for_star(star: int) -> str:
    if star >= 4:
        return "好评"
    if star == 3:
        return "中评"
    return "差评"


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def extract_json(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction from an LLM response.

    Handles code fences, leading/trailing prose, trailing commas, and control
    characters inside strings. Raises only when no JSON object can be recovered.
    """
    if text is None:
        raise ValueError("empty response")
    s = _strip_fences(text)
    candidates = [s]
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        candidates.append(s[start:end + 1])
    last_err = None
    for cand in candidates:
        # First parse exactly as emitted. Most model outputs are already valid JSON;
        # repairing before this check can corrupt strings that contain commas.
        for strict in (False, True):
            try:
                obj = json.loads(cand, strict=strict)
                if isinstance(obj, dict):
                    return obj
            except Exception as e:
                last_err = e
        # Then apply common model slips: smart quotes and trailing commas.
        fixed = cand.replace("\u201c", '"').replace("\u201d", '"')
        fixed = re.sub(r",\s*([}\]])$", r"\1", fixed, flags=re.M)
        for strict in (False, True):
            try:
                obj = json.loads(fixed, strict=strict)
                if isinstance(obj, dict):
                    return obj
            except Exception as e:
                last_err = e
        # raw_decode: parse the first complete object and ignore trailing prose
        try:
            obj, _ = json.JSONDecoder(strict=False).raw_decode(cand[cand.find("{"):])
            if isinstance(obj, dict):
                return obj
        except Exception as e:
            last_err = e
    raise ValueError("no JSON object found: %s" % last_err)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def evidence_found(evidence: str, original: str, translated: str) -> bool:
    e = _norm(evidence)
    if not e or len(e) < 4:
        return False
    return e in _norm(original) or e in _norm(translated)


def postprocess(raw: Dict[str, Any], star: int, original: str, translated: str,
                tax: Taxonomy, min_confidence: float = 0.7) -> Dict[str, Any]:
    """Validate and normalize a model output. Never raises for ordinary model mistakes."""
    reasons = []
    out = {
        "review_type": review_type_for_star(star),
        "facts_original": raw.get("facts_original") or [],
        "facts_translated": raw.get("facts_translated") or [],
        "translation_issues": raw.get("translation_issues") or [],
        "groups": [],
        "needs_human_review": bool(raw.get("needs_human_review", False)),
        "review_reasons": list(raw.get("review_reasons") or []),
        "raw_review_type": raw.get("review_type"),
    }

    model_type = (raw.get("review_type") or "").strip()
    if model_type and model_type != out["review_type"]:
        reasons.append("star_type_conflict")

    # Normalize groups.
    groups = []
    for g in (raw.get("groups") or []):
        if not isinstance(g, dict):
            continue
        l0 = (g.get("l0") or g.get("L0") or "").strip()
        l1 = tax.canonical(g.get("l1") or g.get("L1") or "")
        try:
            conf = float(g.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        if not l1:
            continue
        allowed_l0s = tax.l0s_for(l1)
        if not allowed_l0s:
            reasons.append("label_not_in_taxonomy")
            continue
        if l0 and l0 not in allowed_l0s:
            reasons.append("l0_mismatch")
        true_l0 = l0 if l0 in allowed_l0s else sorted(allowed_l0s)[0]
        l0 = true_l0
        ev = (g.get("evidence") or "").strip()
        if not evidence_found(ev, original, translated):
            reasons.append("evidence_not_found")
            conf = min(conf, 0.5) if conf else 0.5
        groups.append({"l0": l0, "l1": l1, "evidence": ev, "confidence": round(conf, 3)})

    # Review-type rules.
    rt = out["review_type"]
    if rt == "好评":
        # Production rule R1b: 4-5 stars are recorded as 好评/好评.
        if len(groups) != 1 or groups[0]["l1"] != "好评":
            reasons.append("positive_forced_good")
        groups = [{"l0": "好评", "l1": "好评", "evidence": (groups[0].get("evidence") if groups else ""), "confidence": 0.95}]
    elif rt == "中评":
        if not groups:
            groups = [{"l0": "中评", "l1": "无具体指向的差评", "evidence": "", "confidence": 0.5}]
            reasons.append("generic_mid_review")
        for g in groups:
            if g["l1"] == "中评":
                g["l0"], g["l1"] = "中评", "无具体指向的差评"
                reasons.append("generic_mid_review")
    else:  # 差评
        if not groups:
            groups = [{"l0": "差评", "l1": "无具体指向的差评", "evidence": "", "confidence": 0.4}]
            reasons.append("generic_negative_review")

    # Cap at two groups: keep the highest-confidence, then preserve original order.
    if len(groups) > 2:
        reasons.append("multi_label_overflow")
        keep = sorted(range(len(groups)), key=lambda i: groups[i]["confidence"], reverse=True)[:2]
        groups = [groups[i] for i in sorted(keep)]

    # De-duplicate identical pairs.
    seen = set()
    dedup = []
    for g in groups:
        k = (g["l0"], g["l1"])
        if k not in seen:
            seen.add(k)
            dedup.append(g)
    groups = dedup

    if any(g["confidence"] < min_confidence for g in groups):
        reasons.append("low_confidence")
    if any((x.get("type") not in (None, "", "none", "无")) for x in out["translation_issues"] if isinstance(x, dict)):
        reasons.append("translation_conflict")

    out["groups"] = groups
    # Stable de-duplicated reasons.
    clean = []
    for r in reasons + out["review_reasons"]:
        if r and r not in clean:
            clean.append(r)
    out["review_reasons"] = clean
    out["needs_human_review"] = bool(out["needs_human_review"] or clean)
    out["review_type"] = rt
    return out


def confidence_score(pred: Dict[str, Any]) -> float:
    """A simple, deterministic confidence score used for review routing."""
    groups = pred.get("groups") or []
    base = min([float(g.get("confidence") or 0.0) for g in groups] or [0.0])
    reasons = set(pred.get("review_reasons") or [])
    if reasons & {"evidence_not_found", "l0_mismatch", "label_not_in_taxonomy",
                  "star_type_conflict", "invalid_json", "llm_error"}:
        base *= 0.55
    if pred.get("translation_issues"):
        base *= 0.85
    if len(groups) > 1:
        base *= 0.9
    if pred.get("needs_human_review"):
        base *= 0.85
    return round(min(max(base, 0.0), 1.0), 3)


def fallback(reason: str, star: int) -> Dict[str, Any]:
    rt = review_type_for_star(star)
    if rt == "好评":
        groups = [{"l0": "好评", "l1": "好评", "evidence": "", "confidence": 0.0}]
    elif rt == "中评":
        groups = [{"l0": "中评", "l1": "无具体指向的差评", "evidence": "", "confidence": 0.0}]
    else:
        groups = [{"l0": "差评", "l1": "无具体指向的差评", "evidence": "", "confidence": 0.0}]
    return {
        "review_type": rt,
        "facts_original": [],
        "facts_translated": [],
        "translation_issues": [],
        "groups": groups,
        "needs_human_review": True,
        "review_reasons": [reason],
        "raw_review_type": None,
    }
