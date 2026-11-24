# -*- coding: utf-8 -*-
"""Evaluation metrics for multi-label VOC tagging."""
import math
import random
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from .schema import confidence_score
from .taxonomy import Taxonomy

Pair = Tuple[str, str]


def pair_set(groups: Iterable[Dict[str, Any]], tax: Taxonomy) -> frozenset:
    out = set()
    for g in groups or []:
        l1 = tax.canonical(g.get("l1") or g.get("L1") or "")
        l0 = g.get("l0") or g.get("L0") or tax.l0_for(l1) or ""
        out.add((l0, l1))
    return frozenset(out)


def _safe_div(a, b):
    return float(a) / float(b) if b else 0.0


def _f1(tp, fp, fn):
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    return _safe_div(2 * p * r, p + r), p, r


def bootstrap_ci(values: List[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 7):
    if not values:
        return [0.0, 0.0]
    random.seed(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += values[random.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int((alpha / 2) * len(means))]
    hi = means[int((1 - alpha / 2) * len(means)) - 1]
    return [round(lo, 4), round(hi, 4)]


def evaluate(gold_rows: List[Dict[str, Any]], predictions: List[Dict[str, Any]],
             tax: Taxonomy) -> Dict[str, Any]:
    pred_by_id = {}
    for p in predictions:
        pred_by_id[p.get("id")] = p
    rows = []
    for g in gold_rows:
        p = pred_by_id.get(g.get("id"))
        pred = (p or {}).get("prediction") or {}
        rows.append({"gold": g, "pred": pred, "raw": p or {}})

    exact_flags, primary_flags, l0_flags, type_flags = [], [], [], []
    tp = fp = fn = 0
    per_pair_tp = Counter(); per_pair_fp = Counter(); per_pair_fn = Counter()
    queue_flags, wrong_flags = [], []
    invalid = 0
    for r in rows:
        gset = pair_set(r["gold"].get("gold_groups"), tax)
        pset = pair_set(r["pred"].get("groups"), tax)
        exact = (gset == pset)
        exact_flags.append(1.0 if exact else 0.0)
        gold_list = list(r["gold"].get("gold_groups") or [])
        pred_list = list(r["pred"].get("groups") or [])
        gp = (tax.canonical(gold_list[0].get("l1")), gold_list[0].get("l0")) if gold_list else None
        pp = (tax.canonical(pred_list[0].get("l1")), pred_list[0].get("l0")) if pred_list else None
        primary_flags.append(1.0 if (gp and pp and gp == pp) else 0.0)
        l0_flags.append(1.0 if (gp and pp and gp[1] == pp[1]) else 0.0)
        type_flags.append(1.0 if r["gold"].get("review_type") == r["pred"].get("review_type") else 0.0)
        tp += len(gset & pset)
        fp += len(pset - gset)
        fn += len(gset - pset)
        for x in (gset & pset):
            per_pair_tp[x] += 1
        for x in (pset - gset):
            per_pair_fp[x] += 1
        for x in (gset - pset):
            per_pair_fn[x] += 1
        if r["raw"].get("error") or "invalid_json" in (r["pred"].get("review_reasons") or []):
            invalid += 1
        wrong_flags.append(1.0 if not exact else 0.0)
        queue_flags.append(1.0 if r["pred"].get("needs_human_review") else 0.0)

    micro, micro_p, micro_r = _f1(tp, fp, fn)
    all_pairs = set(per_pair_tp) | set(per_pair_fp) | set(per_pair_fn)
    f1s = []
    for x in sorted(all_pairs):
        f, _, _ = _f1(per_pair_tp[x], per_pair_fp[x], per_pair_fn[x])
        f1s.append(f)
    macro = sum(f1s) / len(f1s) if f1s else 0.0

    n = len(rows)
    queue_rate = _safe_div(sum(queue_flags), n)
    err_capture = _safe_div(sum(1 for q, w in zip(queue_flags, wrong_flags) if q and w), sum(wrong_flags))
    queue_precision = _safe_div(sum(1 for q, w in zip(queue_flags, wrong_flags) if q and w), sum(queue_flags))

    metrics = {
        "n": n,
        "exact_set_match": round(_safe_div(sum(exact_flags), n), 4),
        "exact_set_match_ci95": bootstrap_ci(exact_flags),
        "primary_group_match": round(_safe_div(sum(primary_flags), n), 4),
        "primary_group_match_ci95": bootstrap_ci(primary_flags),
        "l0_accuracy_primary": round(_safe_div(sum(l0_flags), n), 4),
        "review_type_accuracy": round(_safe_div(sum(type_flags), n), 4),
        "l1_micro_f1": round(micro, 4),
        "l1_micro_precision": round(micro_p, 4),
        "l1_micro_recall": round(micro_r, 4),
        "l1_macro_f1": round(macro, 4),
        "invalid_output_rate": round(_safe_div(invalid, n), 4),
        "review_queue_rate": round(queue_rate, 4),
        "error_capture_rate": round(err_capture, 4),
        "review_queue_precision": round(queue_precision, 4),
        "tp": tp, "fp": fp, "fn": fn,
    }
    metrics["risk_coverage"] = risk_coverage(rows, tax)
    metrics["slices"] = {
        "by_site": _slices(rows, tax, lambda r: r["gold"].get("site") or "unknown"),
        "by_star": _slices(rows, tax, lambda r: str(r["gold"].get("star"))),
        "by_review_type": _slices(rows, tax, lambda r: r["gold"].get("review_type") or "unknown"),
    }
    metrics["confusion"] = _confusion(rows, tax)
    return metrics


def _slices(rows, tax, keyfn):
    buckets = defaultdict(list)
    for r in rows:
        buckets[keyfn(r)].append(r)
    out = {}
    for k, arr in sorted(buckets.items()):
        exact = []
        for r in arr:
            exact.append(1.0 if pair_set(r["gold"].get("gold_groups"), tax) == pair_set(r["pred"].get("groups"), tax) else 0.0)
        out[k] = {"n": len(arr), "exact_set_match": round(sum(exact) / len(arr), 4)}
    return out


def _confusion(rows, tax):
    """Primary label confusion: gold -> predicted, top 12."""
    c = Counter()
    for r in rows:
        gl = list(r["gold"].get("gold_groups") or [])
        pl = list(r["pred"].get("groups") or [])
        g = tax.canonical(gl[0].get("l1")) if gl else "NONE"
        p = tax.canonical(pl[0].get("l1")) if pl else "NONE"
        c[(g, p)] += 1
    items = [{"gold": k[0], "pred": k[1], "n": v} for k, v in c.most_common(12)]
    return items


def risk_coverage(rows, tax, thresholds=(0.0, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95)):
    """Accuracy on the auto-labeled subset as the review queue grows."""
    scored = []
    for r in rows:
        exact = pair_set(r["gold"].get("gold_groups"), tax) == pair_set(r["pred"].get("groups"), tax)
        scored.append((confidence_score(r["pred"]), 1.0 if exact else 0.0))
    scored.sort(key=lambda x: -x[0])
    n = len(scored)
    out = []
    errors = [x for x in scored if not x[1]]
    for th in thresholds:
        kept = [x for x in scored if x[0] >= th]
        if not kept:
            continue
        caught = sum(1 for x in errors if x[0] < th)
        out.append({
            "threshold": th,
            "coverage": round(len(kept) / n, 4),
            "exact_set_match": round(sum(x[1] for x in kept) / len(kept), 4),
            "queue_rate": round(1 - len(kept) / n, 4),
            "error_capture_rate": round(caught / len(errors), 4) if errors else 0.0,
        })
    return out


def compare(agent: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    keys = ["exact_set_match", "primary_group_match", "l0_accuracy_primary", "review_type_accuracy",
            "l1_micro_f1", "review_queue_rate", "error_capture_rate", "review_queue_precision"]
    return {k: {"agent": agent.get(k), "baseline": baseline.get(k),
                "delta": round((agent.get(k) or 0) - (baseline.get(k) or 0), 4)} for k in keys}
