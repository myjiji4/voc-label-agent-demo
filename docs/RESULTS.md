# Results

## Held-out test (50 reviews, private)

| System | Exact set match | Primary label | L0 accuracy | L1 micro-F1 | Invalid |
|---|---:|---:|---:|---:|---:|
| Old labels + old prompt | 54.0% | 64.0% | 78.0% | 0.691 | 0.0% |
| v2 labels + 6-shot | 44.0% | 64.0% | 80.0% | 0.650 | 0.0% |
| v3 ordered rules + adjudicated gold | **80.0%** | 75.0% | 86.0% | **0.886** | 2.0% |
| v2 predictions, same gold | 46.0% | 64.0% | 80.0% | 0.671 | 0.0% |

95% confidence interval for 40/50 exact match: roughly 67–89%. Treat ±1–2 cases
as noise.

By star bucket (v3):

| Star | N | Exact |
|---|---:|---:|
| 1 | 34 | 76.5% |
| 2 | 3 | 66.7% |
| 3 | 6 | 83.3% |
| 5 | 7 | 100% |

## Residual errors (10 of 50)

| Type | Cases | What happened |
|---|---|---|
| JSON/prose instead of object | 2 | Long reviews; retries still returned analysis text |
| Group count | 5 | Extra support group, missing cancel group, duplicate return group |
| Product severity | 2 | "Broken" vs "unusable" on ambiguous timelines |
| Support tri-state | 1 | Unresolved vs no-reply on one reply-then-silence case |

The remaining errors are adjacent-boundary mistakes, not missing capabilities:
the model finds the right problem family and the wrong sub-label, or keeps the
wrong second group.

## What moved the number

1. Ordered rules + one group per L0: 44% → 78%.
2. Adjudicating the gold set: 72% → 80%.
3. Technical retries/repair: +2 cases, mostly by removing format failures.

Adding more prompt text did not help beyond that. The next lever is a
deterministic group arbiter or a verifier, not a longer prompt.
