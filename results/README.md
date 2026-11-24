# Label-only evidence

`test50_labels.csv` contains one row per record in the internal 50-review test
set:

| Column | Meaning |
|---|---|
| `id` | Sample id (`seq_31` …) |
| `gold_labels` | Owner-adjudicated labels, joined by ` | ` |
| `pred_labels` | Model labels from the frozen v3 run |
| `exact_match` | `1` if the two label sets are identical |

**Review text is intentionally omitted.** It contains customer content and
cannot be published. This file makes the arithmetic checkable:

```
python scripts/verify_results.py
# rows: 50
# exact match: 40/50 = 80.0%
# inconsistent flags: 0
```

What this proves: the count 40/50 and the label pairs are internally consistent.

What it does **not** prove: whether the gold labels themselves are correct.
That requires the private review text and a human reader. Treat the 80% as an
internal measurement, not an independently auditable benchmark.

`test50_metrics.json` stores the same number with a 95% Wilson interval
(roughly 67–89%). A 4-case difference between runs is noise.
