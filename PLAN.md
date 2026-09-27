# Theme 2 Final Plan: Source-Grounded Troubleshooting Compiler

Revised: 21 September 2026

Status: authoritative build plan. This incorporates the final plan agreed in the conversation and the subsequent source-checked revisions. Earlier approach, strategy, optimized-design, and competition-specification documents remain historical references, not additional implementation scope. No application implementation or live model benchmark is claimed by this document.

## 1. Decision and competitive positioning

Build an engine that converts a supplied Samsung support article into a complete, reusable troubleshooting procedure, maps instructions to the exact catalog operations, and explains which source-authored conditions apply to the customer.

Deliver four things:

- The required, independently usable API.
- One polished troubleshooting-and-evidence screen.
- A reproducible comparison against the earlier cached hybrid.
- The prescribed submission artifacts.

The procedure compiler is the core; the adaptive demonstration is deliberately narrow. The pitch is: **We preserve what the support article actually says, distinguish different operations on the same setting, and reuse previous work without reusing the wrong customer assumptions.**

The contribution must be established with measurements. Do not claim globally novel procedure extraction, guaranteed victory, or an unsupported competition score.

Excluded from this build: persistent sessions, autonomous agents, general graph planning, graph visualization, voice, real device control, fine-tuning, local LLM hosting, Redis, multiple backend services, automated provider failover, and a live benchmark dashboard.

Confirmed team assumptions: four members, 6-8 hours each per day, with Python and frontend skills covered. Hosting remains a team computer and public tunnel. No paid service or billing activation is assumed.

## 2. Build specification

### Stack and provisional model selection

Use Python/FastAPI, Pydantic v2, SQLite, and React/TypeScript served by the same deployment. Run one API worker with asynchronous provider requests and warmed local retrieval. Use BM25 and local `all-MiniLM-L6-v2` embeddings for catalog retrieval and semantic-cache candidates; 578 catalog entries do not require a vector database.

**Changed assumption - models are candidates, not a deployment commitment.** Start the day-one feasibility test with `gemini-3.1-flash-lite` for complaint normalization and `gemini-3.8-flash` for article compilation. Their published documentation describes capabilities, including structured output; it does not establish source fidelity or latency on this workload. Before testing, verify that the exact API IDs resolve on the team's account and that usable quotas exist. Keep stage-specific model IDs configurable.

Retain the configuration only if the real end-to-end feasibility runs produce complete, source-supported, contract-valid responses within the measured budgets. A failed candidate triggers a bounded alternative-model test through the same adapter and workload, not an architecture restart. If no available configuration passes, record the failed gate and reduce optional console work while fixing the bottleneck; do not declare feasibility established.

Use structured JSON output, with no web grounding, tool execution, or model-generated URLs. Do not build automatic multi-provider failover. Retain the existing adapter boundary so an unavailable model/provider can be substituted explicitly during configuration.

For each experiment record requested model IDs, resolved versions when exposed, provider, generation settings, account tier/access status, observed quotas and their observation date, token usage, and actual cost basis. Free-tier charges and any hypothetical paid-price estimate must be separate. Unknown cost or unavailable version metadata is recorded as unknown, never silently zero or a pinned version.

References: [Flash-Lite documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [Flash documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). Verify account-specific access during implementation; no API key is needed to approve this plan.

### Interfaces

| Interface | Contract |
|---|---|
| `GET /health` | Exactly `{"status":"ok"}` after storage and indexes are ready. |
| `POST /v1/troubleshoot` | Official `query` and `siis_response:{title,content}` input; only the supplied `ContextDeeplinkResponse` shape on success. |
| `POST /v1/preview` | Same input plus optional explicit facts; returns the official response separately from the selected preview, applicability, source evidence, catalog IDs, and timing/cache diagnostics. |

Use response headers for request ID, cache status, and processing time. No diagnostic, exclusion, applicability, or unsupported-operation fields are added to the official response schema.

The preview is stateless. No accounts, session histories, progress database, or session endpoints are needed. It exposes only information from the current request, not other users' cached sources or traces. Public traffic cannot trigger benchmarks, clear caches, or alter provider configuration.

### Request processing

1. Validate input and hash the complete article title/content plus catalog/pipeline versions. Treat source and complaint text as untrusted data, not executable instructions.
2. Before remote inference, check an exact answer match and then a guarded semantic match within the same article/version boundary.
3. Normalize the complaint, preserving feature area, requested operation, device references, negation, and explicit facts. Unknowns remain unknown.
4. Compile the complete article if no compatible procedure exists. The compiler reads the entire source and compact catalog candidates independently of the complaint.
5. Check the selected setting and operation, then materialize immutable catalog metadata in code.
6. Render and validate the official response. Separately select a complaint-relevant preview and evaluate its source conditions.

Keep two explicit language stages. A fully cold request uses at most two normal-path model calls. A compatible article skips compilation; a safe answer-cache hit requires no hosted model call. Record stage skips. Do not add a third model call merely to approve a semantic cache hit or to repair routine formatting.

### Small internal procedure representation

Use typed records, not a general-purpose knowledge graph:

- Stable source-block IDs and original-text offsets computed by code.
- Procedure groups with feature-area labels, titles, and ordered actions.
- Actions with instruction, condition, warning, and prerequisite references; setting identity; operation; category; and optional catalog ID.
- Explicit prerequisite references and alternative-group identifiers.
- A complete source-coverage ledger.

Operations are `open`, `enable`, `disable`, `update`, or `manual`. The compiler selects source IDs rather than repeatedly generating the article text. Conditions and warnings remain attached to the instruction they qualify. Validate references, duplicate IDs, prerequisite order/cycles, and catalog-operation consistency.

Keep two distinct ledger layers: the immutable compilation ledger accounts for the entire source; the request-specific selection ledger records what the preview includes and why. `excluded - off-topic` is a selection disposition only. It must never remove a procedure from the shared article compilation.

A completed ledger and valid source references are structural checks, not proof of correct extraction or condition binding. Independent annotations establish semantic correctness.

### Completeness, relevance, and the unresolved official interpretation

**Clarified assumption - full-article official output remains the conservative default.** The supplied Theme 2 brief says the output should include all actions, steps, and associated deeplinks. It does not explicitly resolve whether this means every action in a broad article or every action in the complaint-relevant procedure. There is no verified organizer clarification in the workspace.

Until that ambiguity is resolved:

- Compile the complete article internally.
- Keep every source-backed procedure, including its conditions, warnings, prerequisites, and alternatives, in the official response.
- Present a complaint-relevant selected guide in the preview, with the full official response available for inspection.
- Do not silently change the official renderer or its recall denominator to the filtered interpretation.

The preview selects by feature area, not by whether an action's condition is currently true. Include procedures plausibly connected to the complaint and their prerequisite/warning context. Exclude only a clearly different feature with no supporting dependency connection. When relevance is uncertain, retain the procedure and expose the uncertainty. A relevant conditional instruction stays visible even when its condition is false; the applicability label explains that state.

Use the same written relevance rule in runtime selection and independent annotations. For a black-screen complaint, unrelated fingerprint-improvement and Samsung Kids PIN-reset sections receive `excluded - off-topic` in the preview ledger; the compiler retains them and the default official renderer still includes them. Do not classify the whole source as non-actionable because some sections are off-topic.

If written organizer guidance authorizes relevant-only official output, record that guidance and change the official rendering policy, pipeline version, cache boundaries, regression expectations, and output-recall denominator together. The full-article compilation metric remains unchanged. This is a conditional requirements change, not a second implementation mode to build now.

### Formatting and grounding rules

Enforce the FAQ in addition to the supplied schema:

- Exact required goal sentence.
- Titles of two or three words.
- Action descriptions of five to seven words, beginning with `It will`.
- Nonempty contexts, actions, step groups, and steps.
- Finite scores in `[0,1]`.
- No prohibited web addresses, domain fragments, or link/image markup anywhere in the official output, including fallback artifacts.

Use the score as a documented query-to-procedure relevance heuristic, not a correctness probability. Compute it from normalized-query/procedure-text similarity, clamp it to `[0,1]`, and never use it alone to delete source instructions.

Preserve original source text internally. Where the supplied source itself contains a prohibited contact fragment, produce a source-supported, address-free paraphrase without inventing a destination or deleting the surrounding procedure. The malformed Samsung Kids email remains a sanitization test even when that section is excluded from a black-screen preview; preview filtering cannot hide official-output leakage.

### Exact deep-link resolution

Retrieve compact candidates per source block through lexical and semantic matching, including opposite-operation candidates for the same setting where present. Maintain a small catalog setting registry and review ambiguous families rather than building a general ontology.

Distinguish Bluetooth from Bluetooth scanning, enable from disable, navigation from mutation, and Factory data reset from Auto factory reset. Generic button messages are not unique setting identifiers.

Copy actionable links and available validation metadata from the same chosen catalog entry. Missing expected values remain missing. Never manufacture validation values or infer successful execution from a validation URI alone.

An uncertain mapping retains the source instruction as manual with no actionable link. The supplied dummy is only for a genuine unmatched Settings screen and must carry compliant custom text. Destructive actions remain critical. Do not attach a loosely related operation to improve link coverage.

### Guarded reuse

Maintain a bounded, versioned procedure cache and answer cache with SQLite persistence, an in-memory hot cache, and coordination of identical concurrent misses. Partial or failed compilations are never reusable.

- Procedure identity includes article content, compiler/pipeline version, and catalog version. It contains the complete source-backed procedure and resolved mappings, never a query-filtered view.
- Answer identity/compatibility includes the source/version boundary, normalized intent, setting/operation, device references, negation, and relevant explicit facts, including unknown-versus-known state.
- Similarity proposes a candidate; conservative local compatibility checks decide reuse. Ambiguity causes a miss. Calibrate the similarity threshold on development cases and freeze it before holdout testing.
- Changed facts can invalidate an answer while allowing procedure reuse. Changed source or versions invalidate affected artifacts. Recompute preview selection/applicability for the current request; do not reuse a stale customer-specific view merely because the official all-branch guide is reusable.

### Preview semantics and the touch example

**Source-checked clarification - both operations exist in the supplied article.** In `row_21`, the article explicitly offers enabling Touch sensitivity when retaining a screen protector. Elsewhere it instructs disabling the setting when enabled without protective film. These are separately sourced instructions, not an inferred logical inverse.

Evaluate only explicit source conditions using simple fact equality and conjunctions. More complicated conditions remain visible and require confirmation. Initial facts cover protector presence, the customer's intent to keep that protector, sensitivity state, display visibility and touch availability scoped to the relevant display, alternate input availability, HDMI compatibility, backup completion, and whether earlier steps failed. Protector presence alone does not establish the source's retention condition: the enable branch needs confirmation until the intention to keep the protector is known. Treat retention intent as a separate explicit fact in normalization, preview controls, and cache compatibility.

Facts are true, false, or unknown. Do not infer compatibility from an unverified model name or infer that all input is unavailable from failed touch. Preview controls override corresponding query-derived facts for that preview only; clearing a control restores unknown. Reevaluate locally without recompiling the article.

Keep these meanings distinct:

- `applicable`: the instruction exists and its supported requirements are established.
- `not applicable`: the instruction exists but an explicit condition is contradicted.
- `needs confirmation`: the instruction exists but a required fact or condition interpretation is unknown.
- `no source instruction`: the requested operation has no supporting instruction in the supplied source. This is a request-level preview explanation, not a fabricated action or another condition state.

A false condition does not prove the article has no other applicable instruction. An unknown fact does not authorize inventing an operation. To test the missing-inverse boundary, use a clearly labeled synthetic single-branch source containing only the disable instruction; do not claim the unmodified official article lacks an enable instruction.

### Success, errors, and deadline behavior

**Clarified assumption - actionable does not mean automatically executable or deep-linked.**

| Situation | Result |
|---|---|
| Source-supported, nonempty guide meeting the output contract, including manual-only instructions | `200` |
| Malformed request | `422` |
| Valid request whose source genuinely contains no supported troubleshooting/configuration procedure | `422` |
| Provider timeout, malformed/truncated model output, failed compilation, or unusable generated result | Compatible validated fallback if available; otherwise `503` |
| Admission rejected because available inference capacity/quota is exhausted | `429` |

Example manual-only `200`: a supplied article whose procedure consists of holding Power and Volume down for a stated duration and then restarting the device. Preserve the supplied timing/conditions, use manual steps and null/absent links, and satisfy the normal goal/title/description requirements. A Settings link is not required for success.

Example unsupported `422`: a nonempty source containing only device dimensions and warranty definitions, with no troubleshooting instructions, configuration steps, or service-directed action. Do not invent a restart or support referral to make it nonempty.

An unfamiliar article, failed catalog match, complaint/source mismatch, or model returning an empty list is not by itself evidence that the source is non-actionable. Under the default full-article policy, a mismatched but actionable article retains its supported guide; explain the relevance limitation in the preview rather than inventing a fix or returning `422` solely because no preview procedure was selected. Uncertain extraction failures are `503`, not client errors.

Neither `422` nor `503` counts as successful unseen-scenario generalization. Evaluate success as a valid, nonempty, source-grounded guide; a schema-valid empty response or an arbitrary `200` is not sufficient. Report manual-only success separately from link coverage.

Enforce a 7.5-second total application budget including local processing, rendering, validation, and error handling. Reserve the last 0.5 seconds for local completion; do not start/continue hosted inference beyond its remaining budget. Use an outer wall-clock deadline, not only a socket-read timeout. Measure the public eight-second target independently; a 7.5-second backend budget does not guarantee network latency.

On inference timeout or impending deadline, serve only a complete, already validated artifact compatible with the current complaint/intent/facts, exact article content, catalog, and pipeline versions. A cached procedure alone is not permission to return a stale final answer; it can be rendered only if all remaining current-request processing and validation fit the remaining budget. Otherwise return `503`. If the overall budget is exhausted, return the error rather than initiate more fallback work. No remote retry/failover loops or unrelated answers.

Apply bounded inference concurrency and quota-aware admission. Keep secrets in environment variables; exclude credentials and raw customer content from routine logs.

## 3. Evidence and acceptance criteria

### Independent annotation and evaluation sets

Prepare before inspecting final outputs:

- All 20 official inputs and full-source annotations for their 11 distinct articles.
- Exactly nine reviewed, unique paraphrases per official query.
- Six additional articles: three development and three sealed holdout.
- Twelve paired customer-fact cases: six development and six sealed.
- Thirty adversarial operation/cache cases covering negation, opposite operations, changed facts, unknowns, and source/version changes.

Two people independently review important source annotations and reconcile disagreements. Split additional material by article, not by paraphrase. The engine's own extraction inventory or relevance selector cannot label its ground truth.

Annotate every source action and its attached conditions, warnings, prerequisites, alternatives, and feature area. Separately annotate the complaint-relevant procedure using the preview selection rule: clearly unrelated sections may be excluded, uncertain relevance is retained, and false/unknown conditions do not justify omission. Keep whole-article and selected-procedure denominators separate. Synthetic or shortened sources are clearly labeled; never present them as unchanged official material.

Existing probes are reusable development checks, not complete-system accuracy or latency evidence.

### Required regression scenarios

- Both explicitly sourced touch-sensitivity instructions survive with their distinct conditions and correct links; neither is derived by reversing the other's condition.
- A present protector with unknown retention intent leaves the enable branch at `needs confirmation`. Explicitly choosing to retain it establishes that condition; presence alone cannot do so. Changing retention intent reevaluates the preview and answer compatibility.
- With a known contradictory fact, an existing branch is `not applicable`; with an unknown required fact, it is `needs confirmation`.
- A labeled synthetic disable-only source does not acquire an enable instruction on a changed fact/request. The preview explains `no source instruction`; the official response remains schema-compliant and source-grounded without diagnostic fields.
- A black-screen complaint paired with the broad mixed article excludes unrelated fingerprint and Samsung Kids PIN sections from the selected preview, but retains them in compilation and in the default full-article official response. Relevant alternatives and prerequisites stay present.
- Factory reset retains last-resort context, backup instructions, and erasure warnings; it never maps to Auto factory reset.
- Visible display with failed touch is not confused with an invisible display; HDMI compatibility stays unknown without supporting evidence.
- Bluetooth is not confused with Bluetooth scanning; validation values absent from the chosen entry remain absent.
- The actual malformed email produces no prohibited official-output fragment, including when off-topic in the preview.
- A valid manual-only source produces a grounded nonempty `200`; a truly non-procedural source produces `422`; model failures on an actionable source produce `503`, not `422`.
- Changed customer facts reject incompatible answer reuse while reusing the article when valid. Source edits and catalog/pipeline updates invalidate stale artifacts.
- Timeout with a compatible validated artifact serves only that artifact within budget. Timeout with no compatible artifact returns `503`; near-matching or stale artifacts are rejected.
- Unseen articles, malformed model output, timeouts, rate limits, restart recovery, and concurrent identical misses are covered.

### Release targets and denominators

These are targets to measure, not achieved results:

| Area | Target and denominator |
|---|---|
| Official input coverage | 20/20 valid, nonempty successful responses |
| Successful-response contract checks | 100% pass |
| Forbidden output fragments / invented links | Zero observed |
| Grounded step precision | At least 98% of emitted instructions are source-supported |
| Whole-article compilation recall | At least 95% of independently annotated source actions, including alternatives |
| Default official-output source-action recall | At least 95% against the full-article action inventory; do not substitute a filtered denominator |
| Relevant-procedure preview recall | At least 95% against the independently selected relevant procedure, including its prerequisites, warnings, and relevant conditional alternatives even when not currently applicable |
| Exact setting/operation mapping precision | At least 95% of selected mappings |
| Critical warnings and destructive-operation sentinels | No failures |
| Incorrect cache reuse | Zero observed on the adversarial release set |
| Repeat / paraphrase cache hit rate | At least 90% / 80% |
| Public-endpoint repeated-request p95 | At most 300 ms |
| Public-endpoint cold-request p95 | At most eight seconds |
| Supported-condition applicability | At least 95%; count false exclusions and unnecessary confirmations |

Report relevant-procedure selection precision/off-topic inclusion as well as recall, so displaying everything cannot masquerade as accurate relevance selection. Report link coverage alongside link precision, so returning manual steps for every catalog-matchable action cannot appear successful. Report warning/condition binding errors separately from plain action presence.

Count failed and rejected requests, omitted actions, incorrect exclusions, and excessive `needs confirmation` responses. The official gate minima remain distinct from these stronger internal release targets. The supplied materials do not explain how the automated 60 points combine with the jury rubric; do not invent a combined score.

### Day-one cold-path feasibility gate

**Changed execution gate - establish cold-path feasibility before substantial console integration or polish.** On September 21, test the longest supplied articles through the real API and actual public endpoint. Rank unique articles by measured token length for the candidate when available, otherwise record the word/character proxy. Cover at least the three longest unique articles plus a conditional/manual-heavy article if not already among them. Request complete official outputs, not shortened previews.

For every cold observation, clear all request-relevant exact-answer, semantic-answer, procedure, and normalization/result caches if implemented. Keep the normally ready process, catalog index, local embeddings, and connections in a documented startup state. Process startup is a separate measurement. Repeat each selected article twice with fresh relevant caches; these few runs are a feasibility check, not a p95 claim.

Record input size, model/configuration, cache state, normalization time, compilation/extraction time, retrieval/link-resolution time, rendering/validation time, total backend wall time, public client elapsed time, HTTP status, deadline result, and semantic/contract findings. When stages overlap, report their durations and total wall time without summing them as if sequential. Include queue/admission delay in the endpoint measurement.

Evaluate completion and source correctness alongside the 7.5-second internal and eight-second public targets. A fast invalid or incomplete result fails. With genuinely empty relevant caches, a compatible cached fallback normally cannot exist; resulting `503`s are failed completions, not fast successes. Test warm compatible-fallback behavior separately and label it accordingly.

No failing configuration is declared feasible. If the gate fails, prioritize extraction correctness, prompt/output size, model/configuration, and measured bottlenecks before console polish. Do not improve speed by deleting required source content. UI fixtures, layout skeletons, annotations, and submission preparation can proceed in parallel.

### Fair comparison and later p95 benchmark

Compare two configurations with the same models, catalog, materialization/validation, output-completeness policy, resource limits, and evaluation inputs:

1. The earlier query-conditioned hybrid, retaining its existing extraction cache and guarded answer cache.
2. The complete-procedure compiler.

Measure source completeness, condition binding, operation accuracy, incorrect reuse, model calls/tokens, cost, and end-to-end latency. Separate cold, familiar-article/new-intent, exact repeat, paraphrase, and changed-fact workloads. Small offline ablations may disable operation constraints or cache guards; do not build extra production pipelines or weaken the baseline.

Target 60 uncached endpoint observations and 500 cached observations for the final candidate, subject to verified quotas. Publish raw results, sample counts, workload composition, quantile method, completion/timeout rates, and limitations. Successful-completion latency and all-request durations must be separately identified; fast errors must not lower the claimed successful-response p95. Insufficient successful observations or material timeout rates prevent claiming the latency target is established.

A 10,000-entry synthetic cache check demonstrates lookup/storage behavior only, not correctness over 10,000 troubleshooting scenarios. If a feature fails evaluation, narrow its claim or disable it; disclose losing cases.

## 4. Four-person execution plan

| Owner | Responsibility | First integrated deliverable |
|---|---|---|
| Member 1 | API, normalization, compiler, renderer, integration | Real unfamiliar and long articles produce validated official JSON |
| Member 2 | Catalog resolver, caches, deadlines, deployment, timing | Exact operation mapping and an externally measured cold request |
| Member 3 | Independent annotations, relevance/applicability evaluator, benchmarks | Source inventories and fact/relevance labels; day-one quality review |
| Member 4 | Console, evidence presentation, deck, video, submission | Shared-fixture screen skeleton and submission outline; integration after feasibility gate |

Freeze request/procedure types, resolver output, preview fixtures, and current official rendering policy in the first working block. Integrate daily. Members 1-3 jointly review the compiler/resolver/annotation boundary; no author is the sole judge of their own results.

| Date | Completion gate |
|---|---|
| September 21 | Contracts, exact model access/quotas, working real endpoint, longest-article cold-path feasibility with stage timings and manual-only checks; annotations and UI fixtures in parallel. Model retention remains provisional until this passes. |
| September 22 | All official inputs through full-source rendering; operation checks; guarded caches; relevance/applicability preview integrated after the feasibility gate; public endpoint reachable externally. |
| September 23 | Actual fact-change/evidence console; sealed evaluation; fair baseline comparison; larger latency measurements; architecture/model configuration freeze. |
| September 24 | Defect fixes only; fresh-checkout/Docker verification; final results, deck, disclosure, recording, and submission package. |
| September 25 | Access/artifact checks; submit by 6 PM IST, ahead of the supplied 11:59 PM deadline. |

Protect API compliance, source correctness, independent evaluation, and submission artifacts first. If behind, cut console decoration, secondary demo examples, and extra experiments. Do not cut required source coverage, exact operation checks, cache compatibility, or unfamiliar-article support. A delayed feasibility gate consumes optional work time, not the final verification buffer.

Ship automatic applicability recommendations only if their tests pass. Otherwise show source conditions/evidence without an unsupported applicability claim. Do not introduce extra architecture to rescue an unmeasured feature.

## 5. Demonstration and submission

### One-screen product

Provide complaint/article input, a selected relevant guide with conditional branches, a small explicit-facts panel, expandable source/catalog evidence, observed timing/cache status, and a link to the static benchmark report. Make the distinction between the selected preview and the complete official response visible. Explain excluded off-topic sections without mixing exclusion with false or unknown conditions.

No fake device state, animated execution, or simulated success presented as actual device observation. Masked catalog links are mappings, not demonstrated device control.

### Five-minute demo

1. **0:00-0:30 - Problem and contribution.** Explain why a plausible instruction can select the wrong operation, omit a condition, or reuse the wrong assumptions.
2. **0:30-1:30 - Compile and inspect.** Process the actual touch article. Show the enable and disable instructions, their separate source passages, and exact catalog operations. Neither instruction was inferred as the inverse of the other.
3. **1:30-2:30 - Source boundary and changing facts.** Change protector presence, explicit retention intent, and sensitivity facts and show existing branches becoming applicable, not applicable, or needing confirmation while remaining preserved. Protector presence alone must not activate the enable branch. Then show a clearly labeled synthetic single-branch article that contains only the disable instruction. Requesting the absent enable operation produces a preview explanation of `no source instruction`, not invented steps. The official schema is unchanged; the altered article is not presented as original kit material.
4. **2:30-3:10 - Safe reuse.** Show a genuine paraphrase hit and a changed-fact incompatible-answer rejection with compatible procedure reuse. Display real measurements and current-request cache reasons.
5. **3:10-4:00 - Generalization and relevance.** Process a held-out unfamiliar article. Briefly show the mixed black-screen fixture's relevance selection: unrelated Kids/fingerprint procedures are excluded only from the preview under the current default, with full official output available for inspection.
6. **4:00-5:00 - Evidence and limits.** Present the fair comparison, later latency sample sizes, completion rates, manual-only success, and one remaining failure. Show baseline failures only if actually measured.

### Submission package and hosting

Ship code, reproducible README/Docker setup, required `results.jsonl`, raw benchmark records/report, the prescribed deck, a maximum-five-minute video, and AI disclosure. Use exact canonical queries from the SIIS dataset and nine reviewed variations per result. Include the rendering-policy assumption and model/measurement limitations in the report.

Tag the final reviewed submission commit `PRISM_GENAI_HACKATHON_Y2026`. Keep credentials and private benchmark identifiers out of the repository and artifacts.

Host on the agreed team computer, prevent sleep, supervise the process, and verify access from a different network. Confirm the endpoint-update process because a free tunnel URL can change. Hosting availability and free-tier capacity are risks, not production guarantees.

Definition of done: a compliant API, independently checked source fidelity, exact operation mapping, demonstrated compatible reuse, an honest evidence-led demo, and a reproducible submission. No more broad architecture research is required before implementation.

## Revision log and remaining assumptions

- **Touch example corrected against the proposed correction:** kept both operations because both are in the supplied source; made protector retention intent explicit rather than inferring it from presence; added a separately labeled single-branch test and demo for refusing an unsupported inverse. Distinguished not-applicable, unknown-condition, and absent-instruction explanations throughout.
- **Relevance clarified:** added a request-specific `excluded - off-topic` ledger and complaint-relevant preview. Kept conservative full-source official output pending organizer clarification. Added separate full-compilation, official-output, and relevant-preview recall denominators and the mixed-article regression.
- **Failure policy clarified:** manual-only guides can succeed with `200`; non-procedural input and malformed requests use `422`; inference/compilation failures use `503`. Added examples, regressions, and explicit unseen-scoring treatment.
- **Execution gate changed:** longest-article, real-endpoint cold tests now precede substantial console integration/polish. Clear every relevant cache, record every stage and startup state, and treat the small run as feasibility rather than p95 evidence. UI fixtures can still proceed in parallel.
- **Models made provisional:** exact access, quotas, fidelity, completion, latency, and cost determine retention; document resolved IDs/versions and cost basis. No live model selection result is claimed.
- **Timeout behavior tightened:** reserve local completion time, reuse only compatible complete validated artifacts, and count no-fallback cold failures explicitly. The internal deadline does not itself prove the public target.

Remaining risks: the official completeness/relevance interpretation needs clarification; exact account quotas and viable model latency/quality are not yet measured; free-tunnel availability and organizer endpoint-update rules are unverified. These do not require changing the lean architecture, but they must not be reported as solved. The source-backed behavior and current default policy above are explicit so implementation can proceed without silently choosing a different interpretation.
