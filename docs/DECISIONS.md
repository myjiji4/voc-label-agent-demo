# Decision log

This is the short, honest version of how the v3 prompt was reached. The useful
part is the sequence, not the final text.

## 1. Starting point

| System | Exact | F1 |
|---|---:|---:|
| Old labels + old prompt | 54.0% | 0.691 |
| v2 labels + 6-shot prompt | 44.0% | 0.650 |
| Translation-only baseline | 48.0% | 0.724 |

The new label library was cleaner, but the model got worse. Mapping old
predictions onto the v2 label set scored 56%, so the taxonomy itself was not the
problem: the prompt and examples were.

Diagnosis:

- few-shot examples dropped from 10 to 6;
- rules were descriptive prose, with no order and no mutually exclusive
  conditions;
- one pass, no evidence binding, no self-check;
- the model over-used a few labels ("unresolved support" 11 predictions vs 7
  gold; "completely unusable" 6 vs 2);
- translation errors explained only 1 of 13 errors. A translation-only model
  scored 60% on the same 20 cases vs 35% for v2, so the bottleneck was rule
  execution, not input quality.

## 2. v3: make the rules executable

- Each family became a decision list: first match wins.
- One group per L0, at most two groups total.
- Every group carries a verbatim evidence quote and a rule id.
- Eight boundary examples replaced the generic few-shot set.
- The runner retries on empty JSON and repairs malformed JSON.

Result: 20 hard cases went from 7/20 to 20/20, and the full 50-case test from
44% to 78%.

That 20/20 was a warning sign, not a win: those cases had been used to shape the
rules.

## 3. Business definitions exposed a gold-set problem

The owner then defined the boundaries:

- no reply = support never responded;
- slow = support responded, but the wait was too long;
- unresolved = responded in time, did not solve it;
- broken = failed after some use;
- unusable = failed on arrival.

Applying those definitions strictly dropped the score to 66%, then 64%. The
reason was not model behavior: the gold labels contradicted each other.

Examples:

| Same facts | Gold A | Gold B |
|---|---|---|
| Only automated replies, phone unanswered | seq_42 = slow | seq_90 = no reply |
| Initial reply, then silence | seq_32 = slow | seq_63 = no reply |
| Cancel/return message ignored | seq_73 = unresolved | seq_85 = no reply |
| Received defective / never worked | seq_42 = broken | seq_56 = unusable |

No prompt can satisfy both sides.

## 4. Adjudication before further tuning

Eighteen ambiguous rows went into one workbook: original, translation, current
gold, model prediction, ambiguity type, proposed label, question for the owner.
A second sheet paired the contradicting gold labels side by side.

The owner adjudicated all 18. Eleven labels actually changed:

- automatic/template replies do not count as a response;
- "received broken" is `完全不能用`;
- "worked, then failed" is `坏了`;
- a promised replacement with no follow-up is `响应慢`;
- a return in transit that the merchant denies receiving is `退货困难`;
- workmanship complaints with a minor functional issue stay `做工不满意`;
- discount/coupon failures are a support issue, not false advertising.

The original gold file was backed up; the new one is the evaluation baseline.

## 5. Re-run and stop

| Round | Exact | F1 | What changed |
|---|---:|---:|---|
| Adjudicated gold, first run | 72.0% | 0.818 | new gold |
| Format recovery + three rule fixes | 80.0% | 0.886 | retries, support timeline, product timeline |
| One more round | 80.0% | 0.886 | fixed 4, broke 4 |

The last round fixed four cases and broke four. That is the variance floor of
this prompt plus model. Further prompt edits move errors between adjacent
boundaries instead of removing them.

## 6. What I would do next

- Deterministic group arbitration for cancel/return + support combinations
  (the largest residual cluster).
- A verifier pass that checks each label against its rule and evidence.
- A larger gold set before trusting any ±2-case difference.

Not more prompt text.
