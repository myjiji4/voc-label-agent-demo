# -*- coding: utf-8 -*-
"""Run the public demo: 10 synthetic reviews, 4 synthetic examples.

Requires an OpenAI-compatible endpoint:
  export VOC_API_BASE=https://.../v1
  export VOC_API_KEY=...
  export VOC_MODEL=deepseek-v4.1-flash   # or any chat model

Usage:
  python scripts/run_demo.py
  python scripts/run_demo.py --limit 5 --workers 2
"""
import argparse, io, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from voc_label_agent.llm import LLMClient
from voc_label_agent.prompts_v3 import build_messages_v3
from voc_label_agent.schema import extract_json, postprocess, confidence_score, fallback
from voc_label_agent.taxonomy import Taxonomy


def load_jsonl(path):
    return [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]


def dedupe(groups, cap=2):
    best = {}
    for i, g in enumerate(groups):
        if g["l0"] not in best or g["confidence"] > groups[best[g["l0"]]]["confidence"]:
            best[g["l0"]] = i
    keep = sorted(best.values())
    if len(keep) > cap:
        keep = sorted(sorted(keep, key=lambda i: groups[i]["confidence"], reverse=True)[:cap])
    return [groups[i] for i in keep]


def label_one(client, tax, examples, rec):
    last = None
    for attempt in range(3):
        content = ""
        try:
            msgs = build_messages_v3(rec, tax, examples)
            if attempt == 1:
                msgs = msgs + [{"role": "user", "content": "Output ONLY one JSON object with 1-2 groups. No analysis."}]
            elif attempt == 2:
                msgs = [{"role": "system", "content": "Emit ONLY compact JSON: {\"review_type\":\"...\",\"groups\":[{\"l0\":\"...\",\"l1\":\"...\",\"evidence\":\"...\",\"confidence\":0.9}],\"needs_human_review\":false,\"review_reasons\":[]}"},
                        {"role": "user", "content": msgs[-1]["content"][:12000] + "\n\nReturn compact JSON only."}]
            resp = client.chat(msgs, max_tokens=3000)
            content = resp.get("content") or resp.get("reasoning") or ""
            try:
                raw = extract_json(content)
            except Exception as e:
                last = e
                try:
                    rep = client.chat([
                        {"role": "system", "content": "Repair into one valid JSON object. Output JSON only."},
                        {"role": "user", "content": content[:8000]}], max_tokens=3000)
                    raw = extract_json(rep.get("content") or rep.get("reasoning") or "")
                except Exception:
                    time.sleep(1)
                    continue
            pred = postprocess(raw, int(rec.get("star") or 0), rec.get("text_original") or "",
                               rec.get("text_translated") or "", tax, 0.7)
            pred["groups"] = dedupe(pred["groups"], 2)
            pred["confidence"] = confidence_score(pred)
            if not pred["groups"] and int(rec.get("star") or 0) <= 3 and attempt < 2:
                continue
            return {"id": rec["id"], "prediction": pred, "error": None, "raw": content[:2000]}
        except Exception as e:
            last = e
            time.sleep(1)
    return {"id": rec["id"], "prediction": fallback("llm_error", int(rec.get("star") or 0)),
            "error": str(last)[:300], "raw": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--score-only", action="store_true",
                    help="score data/demo_predictions.jsonl instead of calling a model")
    args = ap.parse_args()

    tax = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))
    examples = [r for r in load_jsonl(os.path.join(ROOT, "data", "demo_examples.jsonl")) if r.get("split") == "dev"]
    rows = [r for r in load_jsonl(os.path.join(ROOT, "data", "demo_reviews.jsonl")) if r.get("split") == "test"]
    if args.limit:
        rows = rows[:args.limit]

    preds = []
    if args.score_only:
        cached = {x["id"]: x for x in load_jsonl(os.path.join(ROOT, "data", "demo_predictions.jsonl"))}
        preds = [cached[r["id"]] for r in rows if r["id"] in cached]
        print("demo: %d reviews, model=cached (no API call)" % len(rows), flush=True)
    else:
        client = LLMClient()
        print("demo: %d reviews, %d examples, model=%s" % (len(rows), len(examples), client.model), flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            futs = [ex.submit(label_one, client, tax, examples, r) for r in rows]
            for f in as_completed(futs):
                preds.append(f.result())
                print("done %d/%d" % (len(preds), len(rows)), flush=True)
    order = {r["id"]: i for i, r in enumerate(rows)}
    preds.sort(key=lambda p: order.get(p["id"], 0))

    pm = {p["id"]: p for p in preds}
    exact = 0
    print("\nid | gold | prediction | ok")
    for r in rows:
        gset = {(g["l0"], g["l1"]) for g in r["gold_groups"]}
        pset = {(g["l0"], g["l1"]) for g in (pm[r["id"]]["prediction"].get("groups") or [])}
        ok = gset == pset
        exact += 1 if ok else 0
        gs = " ; ".join("%s/%s" % x for x in sorted(gset))
        ps = " ; ".join("%s/%s" % x for x in sorted(pset))
        print("%s | %s | %s | %s" % (r["id"], gs, ps, "OK" if ok else "X"), flush=True)
    print("\nexact match: %d/%d = %.1f%%" % (exact, len(rows), 100.0 * exact / len(rows)))

    out = os.path.join(ROOT, "runs", "demo-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out, exist_ok=True)
    with io.open(os.path.join(out, "predictions.jsonl"), "w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("saved", out)


if __name__ == "__main__":
    main()
