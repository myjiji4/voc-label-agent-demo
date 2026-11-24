# -*- coding: utf-8 -*-
"""Verify the label-only result export without any model call.

Reads results/test50_labels.csv, recomputes exact match from the label columns,
and checks that the stored exact_match flag is consistent.
"""
import csv, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "results", "test50_labels.csv")
rows = list(csv.DictReader(io.open(path, encoding="utf-8")))
ok = sum(1 for r in rows if r["exact_match"] == "1")
bad = 0
for r in rows:
    g = set(x for x in (r["gold_labels"] or "").split(" | ") if x)
    p = set(x for x in (r["pred_labels"] or "").split(" | ") if x)
    if (g == p) != (r["exact_match"] == "1"):
        bad += 1

print("rows: %d" % len(rows))
print("exact match: %d/%d = %.1f%%" % (ok, len(rows), 100.0 * ok / len(rows)))
print("inconsistent flags: %d" % bad)
