# Iteration log

This repository is a **published snapshot**, not a per-round commit history.
The work happened locally on 2026-11-23 and 2026-11-24 and was pushed as a
snapshot on 2026-11-24. History was not rewritten to simulate a commit-by-commit
narrative; this file is the record of what changed and in which order.

## 2026-11-23

1. Baselined three systems on the same 50-review set:
   old labels + old prompt 54.0% / F1 0.691; v2 labels + 6-shot 44.0% / 0.650;
   translation-only 48.0% / 0.724.
2. Diagnosed the drop: examples reduced from 10 to 6, descriptive rules with no
   order, no evidence binding, no self-check, label-frequency bias.
3. Wrote v3: ordered decision lists, one group per L0, evidence + rule id,
   boundary examples. A 20-case hard subset went 7/20 -> 20/20 and the 50-case
   set 44% -> 78%. The 20/20 was later treated as overfitting, not a result.

## 2026-11-24

4. Business definitions were made explicit: no reply / slow / unresolved;
   broken after use / unusable on arrival.
5. Applying them dropped the score to 66% and then 64%. The cause was found in
   the gold set: several pairs of reviews had identical facts and opposite
   labels (42 vs 90, 32 vs 63, 73 vs 85, 42 vs 56, 63 vs 92, 48 vs 42).
6. Built an ambiguity workbook: 18 rows with original, translation, current
   gold, model prediction, ambiguity type, proposed label, and a question for
   the owner. A second sheet paired the contradicting gold labels.
7. Owner adjudicated all 18; 11 labels changed. `gold_70_v3.jsonl` became the
   evaluation baseline; the v2 file was backed up.
8. Re-ran: 72.0% / F1 0.818. Added format retries and three rule fixes:
   80.0% / F1 0.886.
9. One more round fixed four cases and broke four: 80.0% / 0.886. Declared the
   variance floor and stopped prompt changes.

## What the numbers mean

- 40/50 with a 95% Wilson interval of roughly 67-89%.
- 72% vs 80% is four cases: noise. Do not present it as a significant gain.
- The 20-case 100% was overfitting and is not used as a headline.

## Artifacts

- `results/test50_labels.csv`: label-only export (no review text).
- `results/test50_metrics.json`: 40/50 plus the interval.
- `scripts/verify_results.py`: recomputes the count from the label file.
- `data/demo_predictions.jsonl`: cached demo predictions for offline scoring.
