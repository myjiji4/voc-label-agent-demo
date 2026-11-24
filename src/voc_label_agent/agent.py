# -*- coding: utf-8 -*-
"""The labeling agent: prompt -> structured output -> validation -> review routing."""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from .prompts import build_messages
from .schema import confidence_score, extract_json, fallback, postprocess
from .taxonomy import Taxonomy


class LabelAgent(object):
    def __init__(self, tax: Taxonomy, client, examples: Optional[List[Dict[str, Any]]] = None,
                 mode: str = "bilingual", min_confidence: float = 0.7,
                 review_threshold: float = 0.8):
        self.tax = tax
        self.client = client
        self.examples = examples or []
        self.mode = mode
        self.min_confidence = min_confidence
        self.review_threshold = review_threshold

    def label(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        started = time.time()
        messages = build_messages(rec, self.tax, self.examples, mode=self.mode)
        content = ""
        finish_reason = None
        format_repairs = []
        try:
            resp = self.client.chat(messages)
            content = resp.get("content") or ""
            finish_reason = resp.get("finish_reason")
            # Reasoning models sometimes put the JSON object in reasoning_content
            # when the content budget is exhausted.
            if not content.strip() and resp.get("reasoning"):
                content = resp.get("reasoning") or ""
            try:
                raw = extract_json(content)
            except Exception:
                # One repair round: ask the model to re-emit the same object as valid JSON.
                repair = self.client.chat([
                    {"role": "system", "content": "You repair broken JSON. Output only one valid JSON object. Keep the same meaning and labels. Escape quotes and newlines correctly."},
                    {"role": "user", "content": "Fix this into valid JSON:\n" + content[:8000]},
                ])
                repaired = repair.get("content") or repair.get("reasoning") or ""
                raw = extract_json(repaired)
                format_repairs.append("json_repaired")
                content = repaired
            pred = postprocess(raw, int(rec.get("star") or 0), rec.get("text_original") or "",
                               rec.get("text_translated") or "", self.tax, self.min_confidence)
            score = confidence_score(pred)
            pred["confidence"] = score
            if score < self.review_threshold:
                pred["needs_human_review"] = True
                if "low_confidence" not in pred["review_reasons"]:
                    pred["review_reasons"].append("low_confidence")
            error = None
            usage = resp.get("usage") or {}
        except Exception as e:
            pred = fallback("invalid_json" if "JSON" in str(e) or "Expecting" in str(e) else "llm_error",
                            int(rec.get("star") or 0))
            error = "%s: %s" % (type(e).__name__, str(e)[:400])
            usage = {}
        pred["format_repairs"] = format_repairs
        return {
            "id": rec.get("id"),
            "prediction": pred,
            "error": error,
            "raw_text": (content or "")[:8000],
            "finish_reason": finish_reason,
            "usage": usage,
            "latency_ms": int((time.time() - started) * 1000),
            "mode": self.mode,
        }

    def label_many(self, records: List[Dict[str, Any]], workers: int = 8) -> List[Dict[str, Any]]:
        out = []
        done = 0
        total = len(records)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = {ex.submit(self.label, r): r for r in records}
            for f in as_completed(futs):
                out.append(f.result())
                done += 1
                if done % 10 == 0 or done == total:
                    print("progress %d/%d" % (done, total), flush=True)
        order = {r.get("id"): i for i, r in enumerate(records)}
        out.sort(key=lambda x: order.get(x.get("id"), 0))
        return out
