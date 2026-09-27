# Theme 2 evaluation and release protocol

Version: 1.0 - 21 September 2026. Status: planned protocol; no project evaluation has run.

This document verifies [SPEC.md](SPEC.md) against the scope and targets in [PLAN.md](PLAN.md). All datasets, labels, raw outputs, reports, and submission exports created by this protocol belong inside this project. Supplied parent files remain unchanged.

## 1. Evidence rules and official scoring

Separate four kinds of evidence: deterministic contract checks, independently judged semantic correctness, measured live endpoint performance, and presentation/reproducibility checks. None substitutes for another. Prior parent-folder experiments are development evidence only; their passing checks are not a score for the unbuilt application.

The supplied FAQ describes mandatory gates and an automated 60-point evaluation:

| Official component | Stated requirement or weight |
|---|---|
| Mandatory gates | Healthy API, at least 95% query coverage, at least 90% schema validity, zero prohibited web-URL leaks |
| Schema/formatting | 15 points |
| Catalog links/automatic coverage | 15 points |
| Cache/latency | 15 points; repeat p95 <=300 ms, repeat hit rate >=90%, paraphrase hit rate >=80%, cold p95 <=8 seconds |
| Unseen scenarios | 10 points; valid nonempty responses including new supplied source text |
| Query variations | 5 points; 8-10 diverse unique variations per official query; this project uses nine |

The jury categories are functionality 30%, technical depth/feasibility 25%, originality 20%, relevance 15%, and presentation/documentation 10%. Their combination with the automated 60 points is not disclosed. Do not invent a combined formula, local imitation of an unavailable official scorer, or a 95/100 prediction. The Gemini/Mistral bonus has no disclosed calculation to assign locally.

Our stronger release targets appear below. A local pass means passing this protocol, not receiving those official marks.

## 2. Data, splits, and annotations

### Dataset inventory

| Set | Size | Use |
|---|---|---|
| Official input set | 20 exact canonical SIIS queries, 11 distinct articles | Required-input coverage and full-source labeling; public development material |
| Official paraphrases | Nine per query, 180 total | Export validity and genuine semantic-reuse tests |
| Additional articles | Six: three development, three sealed holdout | Generalization beyond public source articles |
| Fact-change pairs | Twelve pairs: six development, six sealed | 24 cases with expected condition/applicability changes |
| Operation/cache adversaries | 30 cases | Negation, wrong settings/operations, unknowns, stale versions, and unsafe reuse |
| Failure/contract fixtures | Cases in the matrix below | Deterministic mutation, error, and structural checks |

Give every case a stable ID, provenance, source hash, expected outcome, split, and reviewer labels. Clearly mark team-authored, externally supplied, shortened, and synthetic articles. External material becomes runtime knowledge only when explicitly supplied as the request's SIIS source; the engine must not browse for it.

Store unchanged imported inputs in `data/official/`, case/split manifests and annotations in `data/annotations/`, and synthetic/additional source material in `data/fixtures/`. Import manifests record the original archive and nested-entry hashes. Do not use the Theme 5 harness as a Theme 2 scorer.

Split by article/family, never only by paraphrase. Holdout cases must not be used to tune prompts, retrieval aliases, thresholds, or model choices. After a holdout failure informs a fix, label that set exposed/development and use fresh independently labeled cases for any new held-out claim. If time prevents replacing it, disclose the limitation.

### Annotation procedure

Two reviewers independently label important articles/cases before seeing final candidate outputs, then reconcile disagreements. The engine author cannot be the sole judge. The compiler's own source ledger or selector is not ground truth.

For each article enumerate actions, required instruction units, attached conditions and warnings, prerequisite order, alternatives, destructive categories, feature area, and admissible catalog setting/operation IDs. Semantic equivalence is allowed; wording similarity alone is insufficient. Preserve unknown catalog matches rather than invent a label.

Create a separate per-complaint relevant-procedure inventory: include plausibly connected feature areas and prerequisite/warning context; exclude only clearly different features with no dependency connection. Retain uncertain relevance. False or unknown conditions do not remove relevant conditional actions.

Keep three inventories distinct:

1. Full source action inventory for compilation.
2. Full source action inventory for the current official renderer.
3. Independently selected relevant procedure for the preview, with `excluded - off-topic` reasons.

Do not change an inventory after observing an omission merely to improve recall. Report reviewer disagreements and resolutions. The original touch article contains both operations; retention intent is distinct from protector presence. A missing-inverse fixture must be explicitly labeled as a synthetic single-branch source.

## 3. Requirement-to-test matrix

| ID | SPEC coverage | Case and expected result |
|---|---|---|
| T01 | S01 | Hash all protected original inputs before/after import and evaluation; unchanged. Imported copies match their source entries. All generated files stay inside the project. |
| T02 | S02 | Ready health response is exactly `{"status":"ok"}`. Malformed/blank requests return 422. Preview fields never appear in official success JSON. |
| T03 | S03, S04 | All 20 official cases produce a source-grounded nonempty guide. Every source branch and required context is accounted for independently of complaint. |
| T04 | S02, S04 | Mutate titles, description lengths/prefixes, goal punctuation, score NaN/range, empty lists, and extra diagnostic fields; reject invalid successful output. |
| T05 | S04 | Test actual malformed Kids email plus web URLs, domain fragments, Markdown links/images, and HTML link/image tags; zero prohibited official-output strings, including fallback paths. Preserve procedural meaning after sanitization. |
| T06 | S05 | Enable/disable reversal, Bluetooth/scanning confusion, and Factory data reset/Auto factory reset mismatch are rejected. Independently inspect jointly wrong intent-plus-link cases that structural checks can miss. |
| T07 | S05 | URI/key-only validation remains incomplete; no validation stays absent; metadata comes from the same entry. Reject invented values and opposite-operation metadata. |
| T08 | S05, S08 | Physical-only supported procedure succeeds with 200 and manual/null links. Genuine unmatched Settings screen alone can use the supplied dummy with compliant custom text. |
| T09 | S03, S06 | Original touch source retains separately sourced enable and disable instructions. Protector present but retention unknown => needs confirmation for the enable condition. Known contradictory condition => not applicable. |
| T10 | S06 | Synthetic disable-only article plus request for absent enable operation => no invented instruction; preview explains no source instruction, separate from unknown/not-applicable states. |
| T11 | S04, S06 | Mixed black-screen article: Kids/fingerprint sections remain in compilation and default official output, but are excluded from the selected preview with off-topic reasons. Relevant conditional branches remain visible. |
| T12 | S03, S06 | Visible screen/broken touch versus invisible screen; scoped inner/cover display facts; alternate input and unknown HDMI compatibility. No unsupported capability inference. |
| T13 | S03-S06 | Factory reset preserves last-resort requirement, backup prerequisite, erasure warning, order, and critical category. No prior-step failure or backup-completion assumption. |
| T14 | S07 | Genuine paraphrases may reuse compatible answers. Near-matches changing negation, setting, operation, device, protector retention, or other facts reject incompatible reuse while retaining valid procedure reuse. |
| T15 | S07 | Source edits and catalog/pipeline changes invalidate affected artifacts; unknown-to-known fact changes cannot reuse an incompatible view. Failed/partial artifacts never enter reusable caches. |
| T16 | S07 | Concurrent identical misses share compilation; other requests do not receive another caller's facts or preview. Restart preserves valid persisted artifacts and version checks. |
| T17 | S08 | Descriptive-only non-procedural source => 422. Empty/malformed model result on actionable source => 503, not 422. Mismatch alone does not reject an actionable source. |
| T18 | S08, S09 | Timeout with compatible validated artifact returns only that artifact within budget; timeout with none or a stale/near-matching artifact => 503. No unrelated fallback. |
| T19 | S09 | Quota/admission rejection => 429. No retry cascade, extra repair model call, or work beyond total deadline. True cold requests clear all relevant result caches. |
| T20 | S03, S10 | Source prompt injection cannot override extraction rules, obtain secrets, execute code, choose arbitrary URLs, or bypass validation. Logs/errors contain no credentials or other users' data. |
| T21 | S02-S09 | Three sealed unfamiliar articles and sealed fact pairs use the real pipeline, not row IDs, prerecorded responses, or source-specific output fixtures. |
| T22 | S11, S12 | Clean-checkout reproduction, external endpoint, submission JSONL, nine variations, deck/video/disclosure copies, final tag, and provenance checks pass. |

Mocked transport and deterministic mutations test behavior, not real model performance. Give each test a recorded status of NOT RUN, PASS, FAIL, or BLOCKED with evidence and reasons. Do not label planned checks as passing.

## 4. Metrics and release targets

Compute both counts and rates. Quality matching must check meaning and required context, not merely source-reference existence. Distinct expected actions cannot be satisfied by duplicating one output action.

| Metric | Definition and target |
|---|---|
| Official success coverage | Valid, nonempty, source-supported 200 responses / 20 required queries; target 20/20 |
| Contract validity | Official 200 responses passing schema plus FAQ checks / all official 200 responses; target 100%; also show failures over all attempts |
| Grounded step precision | Emitted instructions supported in their stated context / all emitted instructions; >=98% |
| Whole-article compilation recall | Correctly represented annotated source actions / all expected source actions; >=95% |
| Official full-source action recall | Correctly rendered annotated actions / all expected full-article actions; >=95% under current policy |
| Relevant-preview recall | Correctly retained expected relevant actions, including required context and conditional alternatives / all independently expected relevant actions; >=95% |
| Preview selection precision | Selected actions belonging to the independent relevant inventory / all selected actions; report count/rate and off-topic inclusions |
| Exact operation mapping precision | Correct setting-and-operation mappings / all selected actionable mappings; >=95% |
| Mapping coverage | Correctly linked source actions / independently catalog-matchable source actions; report separately from precision and manual-only cases |
| Critical sentinels | Critical actions retain required warnings/prerequisites/category and never map to a different destructive operation; zero failures |
| Wrong cache reuse | Incompatible answers served / adversarial reuse opportunities; zero observed, with sample count |
| Repeat hit rate | Exact/semantic answer hits / measured exact-repeat requests; >=90%; procedure-only hits do not qualify |
| Paraphrase hit rate | Compatible answer hits / measured genuine non-identical paraphrase opportunities; >=80% |
| Applicability correctness | Correct states / independently labeled supported-condition decisions; >=95%; show false exclusions and unnecessary confirmations |
| Output leaks/invented links | Absolute counts across all tested successful responses and fallback responses; zero |
| Endpoint latency | Public repeated-request p95 <=300 ms; public fully cold p95 <=8 seconds; separate from backend <=7.5-second deadline |

Report warning/condition binding and prerequisite preservation separately even when action presence is correct. A missing/failed response contributes zero recovered actions to recall and fails coverage; it is not dropped from the dataset. Precision with no emitted instructions is undefined, not 100%. Report all-error runs as failures, never high-quality empty output. Keep per-case results alongside aggregate and per-article summaries so long articles do not hide weak cases.

If organizer guidance later authorizes relevant-only official output, change its expected inventory and policy/version together in all three documents. Whole-article compilation recall must remain unchanged. Do not silently relabel preview recall as official full-source recall.

## 5. September 21 cold-path feasibility gate

Purpose: discover whether the actual two-stage pipeline can process the largest inputs correctly and promptly before substantial console integration/polish. UI fixtures, annotations, and submission outlines can proceed in parallel.

1. Verify exact candidate model IDs resolve on the account; record tier, available quotas, generation settings, and any observed limits. Candidates remain provisional until tested. Do not activate billing implicitly.
2. Rank unique supplied articles by measured candidate token length where available; otherwise name the word/character proxy. Select at least the three longest unique articles and a conditional/manual-heavy case if not already covered.
3. Start the service normally and warm required local catalog/embedding indexes. Record startup/connection state; test process startup separately from a ready-service cache miss.
4. For each measured request clear its exact/semantic answer, procedure, and any normalization/result caches. Do not preload official outputs. Repeat each selected article twice with fresh relevant caches.
5. Send requests through the actual public endpoint. Include the full normalization, compilation, link resolution, full official rendering, and validation path; never benchmark a shortened preview as the official output.
6. Record each stage, queue/admission, total backend wall time, public elapsed time, HTTP outcome, output validity/completeness, model calls, tokens, and cache state. Report overlap honestly rather than adding parallel durations as wall time.
7. Verify the 7.5-second internal deadline with 0.5 seconds reserved for local completion, and measure the eight-second public target independently.

A run fails feasibility if it is fast but invalid/incomplete, exceeds a budget, or fails to complete. With truly empty relevant caches, cached fallback is normally impossible: record the resulting 503 as a failed completion, not a fast success. Evaluate compatible warm fallback in a separate named workload.

This small sample is an early feasibility check, not p95 evidence or an accuracy estimate. Retain model configuration only after it passes the tested cases; do not claim general performance from this gate. On failure, record the cause, adjust the bounded candidate/configuration or measured bottleneck, and rerun the same gate with a new run ID. Do not remove source content to reduce latency.

## 6. Fair comparison and final latency protocol

### Architecture comparison

Compare the final compiler with the earlier query-conditioned hybrid using the same models, sources, catalog, output policy, materialization, validators, and resource limits. Preserve the hybrid's existing extraction and answer caches. Document the baseline's actual extraction-cache behavior; do not manufacture a benefit by disabling it or requiring it to omit branches.

Compare source/condition fidelity, exact mappings, incorrect reuse, calls/tokens, cost, and latency on identical case sets. Small offline operation-constraint and cache-guard ablations are allowed, not extra production pipelines. If only extraction conditioning is changed, call the result a conditioning experiment rather than a complete architectural comparison.

Label workloads separately:

- Fully cold new article/new query.
- Familiar compiled article/new intent.
- Exact repeat.
- Genuine paraphrase with unchanged facts.
- Adversarial near-match/changed fact.
- Changed article/catalog/pipeline version.
- Compatible fallback and provider-failure cases.

Alternate candidate/baseline order across cases to reduce time-of-day/provider-order bias. Use the same documented seed for randomized ordering. Do not tune on sealed results.

### Cache measurement

Seed canonical answers through successful real pipeline requests. Measure non-identical paraphrases against a documented seed state; do not count a previously warmed exact paraphrase as a first semantic hit. Keep seed requests outside timed-repeat denominators, while reporting their setup cost/calls. Isolate cache namespaces between configurations. A semantically similar but incompatible hit fails correctness even if fast.

Target 500 cached-workload observations, with 250 exact-repeat and 250 genuine-paraphrase observations balanced across official queries. Report first-exposure semantic hit rates on the 180 unique variations separately from later repeats. If repetitions are needed for latency samples, identify them and do not let exact repeats inflate the semantic hit-rate metric.

### Cold latency and statistics

Target at least 60 uncached end-to-end observations for the final candidate across article lengths and scenario families, including the sealed unfamiliar sources. Clear relevant result caches for each fully cold observation, keep the ready-service setup documented, and record actual calls rather than assuming two succeeded. Familiar-article/new-intent runs are separate from fully cold runs.

Measure elapsed time with a monotonic clock at the public client. Use nearest-rank p95: sort durations and select rank `ceil(0.95 * n)`. Report n, p50, p95, maximum, success counts, deadline exceedances, timeout rate, and workload composition. Report exact, paraphrase, and pooled cached latency separately.

Publish successful-completion latency separately from all-request duration; fast 429/503 responses must not lower a claimed successful p95. Non-completions remain failures in the overall completion/SLO report. Fewer than the planned observations or material timeout rates limit the claim even if a small successful subset is fast. Quota limitations reduce the documented sample size; never fabricate missing results or evade account limits.

The 10,000-entry synthetic cache test measures lookup/storage behavior only. Record configured bounds and concurrency; it is not 10,000-scenario semantic accuracy or uncached provider capacity.

## 7. Reports, artifacts, and privacy

Store each run under `reports/<run-id>/` and do not overwrite earlier evidence. Planned contents:

- `manifest.json`: timestamp, revision/content fingerprint, dataset/split hashes, catalog/pipeline/prompt versions, model IDs and resolved versions if exposed, generation settings, account tier/quota observations, endpoint environment, hardware, cache setup/bounds, seed, thresholds, and output policy.
- `observations.jsonl`: one record per attempt with case/configuration/workload, timings, status/error class, stage execution/skips, cache decision/reason, calls, tokens, and actual cost basis.
- `outputs.jsonl`: test request/response and relevant compiler/preview evidence for approved benchmark data only, linked by case/attempt ID.
- `judgments.jsonl`: independent labels, matches, errors, reviewer disagreement resolution, and pass/fail findings.
- `metrics.json` and `REPORT.md`: counts/denominators, quality, latency, completion, cost, comparison, limitations, and release decision.

Raw test outputs are not the submission-format `results.jsonl`. Export that separately to `submission/` using exact canonical `original_query`, nine reviewed variations, and the required response wrapper/shape. Validate both export structure and each contained official response against the supplied requirements before submission.

Record actual charges and their source. Zero observed free-tier charges do not imply unlimited capacity. Label any paid-price projection separately; unavailable tokens/cost/version data stays unknown. Never store API keys, authentication headers, account identifiers, private customer text, or hidden model reasoning in these reports.

Archive failed runs as well as successful ones. Every claim in the deck/video should trace to a report and case/sample count. Show only genuinely observed baseline failures. Synthetic missing-inverse demos and masked links must be labeled honestly.

## 8. Release and handoff checklist

- All deterministic contract and critical safety sentinels pass; official 20/20 coverage and semantic targets are measured.
- Preview relevance and applicability are independently evaluated; no unsupported feature claims. If applicability fails, expose source conditions without automatic applicability claims.
- Model/access and day-one cold gate are recorded; later p95 results are distinct and include sample limitations.
- Cache compatibility tests, timeout/no-fallback handling, restart, and concurrent-miss checks pass.
- A fresh checkout with required authorized input copies reproduces startup and the documented checks; no hidden dependency on the author's parent paths or cached official answers.
- Original supplied artifacts still match provenance hashes. Working deck/disclosure copies and all generated outputs remain in the project.
- Public endpoint passes an external-network check; hosting/URL-change limitations are disclosed.
- `submission/results.jsonl`, prescribed deck, maximum-five-minute video, AI disclosure, and reproducibility instructions are reviewed; tag the final reviewed commit `PRISM_GENAI_HACKATHON_Y2026` when submitting.

At protocol authoring, the result was **NOT RUN**. Current per-case statuses
and local measurements are recorded in `reports/RELEASE_STATUS.md` and
`reports/FINAL_REPORT.md`. Local checks do not establish hosted feasibility,
public endpoint latency, independent semantic metrics, or a competition score.
