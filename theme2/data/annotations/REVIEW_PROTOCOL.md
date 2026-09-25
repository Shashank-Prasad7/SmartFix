# Independent review protocol

The nine files in `review_pack/` contain **blank** reviewer fields. They are
source-first materials, not labels or evaluation results. `manifest.json`
records 20 public queries, 11 unique supplied articles, three team-authored
development articles, six team-authored fact pairs, 30 synthetic cache
adversaries, and 180 generated variations. No sealed holdout articles or labels
have been invented. The team-authored expected states used in unit tests are
development assertions and do not count as independent judgment.

## Reviewer sequence

1. Give reviewer A and reviewer B separate copies of their four sheets. They
   should not see the compiler output, each other's labels, or the development
   unit-test expectations before submitting their first pass.
2. In each article sheet, enumerate distinct source actions and required
   instruction units. Record source spans, conditions, warnings, prerequisites,
   alternatives, feature areas, and defensible catalog setting **and** operation
   IDs. Mark uncertain matches as uncertain or manual. A source line with two
   distinct operations may require two action labels.
3. In each query sheet, list actions relevant to the complaint separately from
   the full-source inventory. Keep plausibly connected prerequisites and warnings;
   exclude only clearly unrelated features. Label supported applicability as
   applicable, not applicable, or needs confirmation. Record the fact evidence.
4. In each fact-pair sheet, label both sides independently; do not infer the
   changed label from the test fixture's expected value. Check scope, especially
   inner versus cover display and protector presence versus retention intent.
5. In each variation sheet, judge whether the variation preserves the canonical
   complaint's intent and facts and whether it is meaningfully distinct. The
   nine variants were generated mechanically and must not be presumed valid.
6. Reconcile disagreements after both first passes are frozen. Preserve both
   original files and record adjudication, rationale, and reviewer identities in
   a separate `judgments.jsonl`. The engine author alone cannot adjudicate.

## Sealed evaluation

An independent party should supply three unfamiliar article families and six
fact-change pairs with their own stable IDs and labels. Keep them out of code,
prompts, retrieval aliases, and threshold tuning. Freeze pipeline version and
configuration before the first run. If a holdout failure drives a fix, mark that
set exposed/development and obtain a fresh sealed set for a later holdout claim.

## Scoring

Match output actions one-to-one to the reviewer inventory, including required
context and conditional alternatives. Count an error or missing response as zero
recovered actions. Report counts and rates per article and in aggregate for
whole-source compilation, official rendering, preview recall and precision,
grounded step precision, exact operation mapping, applicability, warnings, and
prerequisite order. A schema pass or source-reference match does not establish
semantic correctness. Preserve the full-article official-output denominator.

Run `python -m theme2.scripts.prepare_review --check` from the PRISM root to
check that the blank pack still matches the current inputs. Do not rerun the
creation command over reviewer work.
