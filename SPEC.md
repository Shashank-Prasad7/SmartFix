# Theme 2 implementation specification

Version: 1.0 - 21 September 2026. Status: specification, not implemented behavior.

This document operationalizes [PLAN.md](PLAN.md). [EVAL.md](EVAL.md) defines verification. No new product scope is introduced. Requirement IDs below are used by the evaluation protocol.

## S01. Workspace and trusted inputs

All new implementation and outputs live under `theme2/`. Parent hackathon inputs remain unmodified. Treat earlier parent experiments as development references, not a production package to execute in place.

Verified input copies are available in `data/official/`. The outer archive is `data/official/archives/participant-kit-all-themes.zip`; its `participant-kit/Theme02_Input_Kit.zip` entry is also copied to `data/official/archives/Theme02_Input_Kit.zip`. The needed `siis_responses.json`, `deeplinks.json`, `schema.py`, `input.txt`, and `sample_output.json` are extracted byte-for-byte into `data/official/student_kit/`. Read these project-local inputs; parent paths are not runtime dependencies. The brief/FAQ and templates are under `data/official/documents/` and `data/official/templates/`. Provenance, byte sizes, and archive/entry SHA-256 hashes are in `data/official/manifest.json`. Future imports must validate named archive entry paths and preserve bytes; never blindly extract arbitrary paths. The other participant harness in the outer archive is for Theme 5 and has not been extracted as this project's scorer.

Use SIIS `original_query` as the canonical offline query. The supplied schema establishes field shapes but permits values the FAQ forbids, including empty guides. The supplied sample is illustrative and has formatting discrepancies; enforce the FAQ rather than copying those mistakes. Never edit the originals to make validation pass.

The current kit has 20 queries, 11 unique article payloads, and 578 catalog entries. These are fixture inventory checks, not hardcoded runtime routing rules. Unseen queries and articles must use the same real pipeline.

## S02. Service and API contract

Use FastAPI, Pydantic v2, SQLite, one backend worker, and a React/TypeScript console served from the same deployment. Warm the local catalog and embedding indexes before reporting ready. No persistent sessions or extra services.

### Required endpoints

- `GET /health`: `200` with exactly `{"status":"ok"}` only when ready; return a non-success readiness response while initialization has failed or is incomplete.
- `POST /v1/troubleshoot`: accepts `query: string` and `siis_response: {title: string, content: string}`. Reject blank query/content and structurally malformed input as `422`; do not silently truncate source text.
- Success body is exactly the official `ContextDeeplinkResponse` hierarchy. No additional trace, fact, source, or error fields appear inside that success body.

Official response hierarchy:

```text
ContextDeeplinkResponse
  contexts[]
    goal, title, score
    actions[]
      actionName, description, category
      stepGroups[]
        steps[]
        actionableDeeplink?  (official Deeplink)
        validationDeeplink?  (official ValidationDeepLink)
```

Use `auto`, `manual`, or `critical` categories. Destructive instructions remain critical even when a mapping exists. Automatic step groups must have a supported actionable link. Manual and critical instructions may have no link. Follow original optional/null field semantics.

Return request ID, cache status, and total application time through `X-Request-ID`, `X-Cache-Status`, and `X-Processing-Time-Ms` headers. Cache status distinguishes exact answer, semantic answer, procedure reuse, miss, and compatible fallback; do not call procedure reuse an answer-cache hit.

### Preview interface

`POST /v1/preview` accepts the official request plus `facts`, an optional map of supported fact keys to `true`, `false`, or `null` (unknown). Return:

- `response`: the unmodified official response for the request.
- `preview`: selected procedure/action IDs, selection reasons, applicability states, and request-level source limitations.
- `evidence`: source references and selected catalog metadata needed to inspect this request.
- `trace`: request ID, cache decisions/reasons, model-stage execution/skips, and stage timings.

This is a separate diagnostic contract. Do not add these fields to `/v1/troubleshoot`. Preview fact overrides affect the preview, not the caller's source or a shared cached procedure. Do not store a customer session. The endpoint must not expose other callers' cache records, secrets, hidden model reasoning, or arbitrary server files.

## S03. Pipeline and intermediate records

Implement this flow: validate -> answer-cache lookup -> complaint normalization -> procedure-cache lookup/complete compilation -> link checks/materialization -> full official rendering/validation -> cache admission. Preview selection and applicability are separate projections of the completed procedure.

There are two explicit language stages and at most two normal-path hosted calls on a fully cold request. Cache hits skip completed work. Neither stage may browse for replacement troubleshooting advice or execute source instructions. Stage 2 compiles independently of the complaint; article reuse must not preserve query filtering.

Use small typed records:

| Record | Required information |
|---|---|
| Normalized complaint | Technical complaint, feature area, requested operation, explicit device/app references, negation, explicit facts with evidence, unresolved interpretation |
| Source block | Stable ID, original text, code-computed character offsets, article hash |
| Procedure | ID, source-backed topic/title, ordered actions, source references |
| Action | ID, source instruction references, setting identity, operation, category, condition/warning references, prerequisite IDs, alternative group, optional catalog ID |
| Compilation ledger | Disposition of every source block as procedural content, attached context, or non-procedural content, with a reason |
| Selection ledger | Per-request inclusion, uncertain relevance, or `excluded - off-topic`, with a reason |

Operation values: `open`, `enable`, `disable`, `update`, `manual`. Retain unrecognized condition text rather than forcing it into executable logic. Prerequisite references must exist and form a valid ordering; alternatives must not become a mandatory sequence. Do not introduce a general graph planner.

Model outputs may select source/candidate IDs but may not invent offsets, URIs, or validation metadata. Structural validation checks IDs, ordering, full block accounting, and catalog compatibility. Independent labels, not the compiler's own ledger, determine semantic completeness.

## S04. Source coverage and deterministic rendering

Current policy: compile and render all source-backed procedures in the official response. The brief's wording about all actions remains ambiguous for multi-topic articles; relevant-only official output is not authorized by this plan. Keep policy/version information in internal configuration and benchmark manifests, not extra official fields.

Render ordered source-backed instructions with their warnings, conditions, prerequisite context, and relevant alternatives. Unknown and false conditions do not remove the source instruction. A complaint mismatch must not generate an outside remedy or automatically reject an otherwise actionable source.

Enforce:

- `Follow these steps to perform this <Name> Troubleshooting.` or the corresponding `Configuration.` sentence, including final period.
- Context title: 2-3 whitespace-separated words. Action description: 5-7 words beginning `It will`. Whitespace counting is a documented local convention; no official tokenizer is supplied.
- Nonempty content throughout the required lists, finite numeric score in `[0,1]`, and no undeclared official fields.
- Recursively check all official-output strings and keys for prohibited HTTP(S)/web-domain fragments, `.com`, `.html`, Markdown links/images, and link/image tags. Approved catalog Bixby URIs are permitted.

Generate score from clamped local similarity of the normalized complaint to short procedure title/action text. This is relevance, not a calibrated correctness probability; never use it alone to delete an action.

Retain original evidence privately. For a prohibited contact fragment in the source, allow only a source-supported, address-free paraphrase preserving the procedure's meaning. Never invent a new destination or quietly omit the action. If faithful valid rendering cannot be established, treat the result as unusable rather than deliver invalid output. The malformed Samsung Kids email must still be handled when the selected preview is about black screens.

## S05. Deep-link resolver

Prepare a small setting registry from catalog descriptions, Q&A descriptions, validation keys when available, and operation metadata. Use BM25 plus warmed local MiniLM embeddings to propose compact per-block candidates. Include opposite-operation candidates when present so interpretation must distinguish them.

The compiler identifies the setting/operation and selects a candidate; code checks the registry compatibility and materializes that entry. Generic messages alone cannot establish identity. A structurally compatible mapping is not proof of correct language interpretation; EVAL includes joint intent/link mistakes.

Required distinctions: Bluetooth versus scanning/Music Share, enable versus disable, navigation versus mutation, and Factory data reset versus Auto factory reset. Preserve source-supported target values for update operations; do not imply that masked links actually changed a device.

Copy actionable metadata and available validation metadata from the same immutable entry. Preserve incomplete URI/key-only validation; do not invent expected values. If that entry has no validation, emit null/absence according to the schema. A validation read is not proof of successful execution.

If uncertain, keep the instruction manual/null, or critical/null for a destructive action. Use `bixby://dummy_positive` only for a genuine unmatched Settings screen and provide the required concrete 5-7-word description/message. Do not use it for every missing mapping or ordinary physical instruction.

## S06. Relevance and applicability preview

Select procedures plausibly connected to the normalized complaint's feature area. Include their prerequisite/warning context. Exclude only clearly distinct features without a dependency connection; retain uncertainty. This exact rule governs human relevance labels in EVAL.

An unrelated Samsung Kids PIN or fingerprint section may be `excluded - off-topic` in a black-screen preview. It remains in compilation and the current official response. Do not confuse off-topic with an unmet condition.

Facts include protector presence, protector retention intent, touch-sensitivity state, display visibility/touch availability scoped to the affected display, alternate input availability, HDMI compatibility, backup completion, and prior-step failure. Each fact is explicit true/false/unknown with provenance. Do not equate protector presence with wanting to retain it, infer HDMI support from a model name, or equate failed touch with the absence of alternate input.

Known preview overrides take precedence over the corresponding query-derived fact only for that preview. An explicit null restores unknown. Preserve the distinction between override and query evidence and recompute the preview rather than store the override in a shared artifact.

Evaluate simple source fact equality/conjunctions locally:

- `applicable`: supported conditions established.
- `not applicable`: an explicit source condition contradicted.
- `needs confirmation`: a required fact/interpretation unknown.

More complex conditions stay textual and need confirmation. `no source instruction` is a separate request-level explanation when a requested operation is absent; it is not an action or a fourth truth value.

The original touch article contains both enable-when-retaining-protector and disable-when-enabled-without-film instructions. Preserve both. Use a labeled synthetic single-branch source to test that changing facts never invents a missing inverse. Merely having a protector does not activate the enable branch without retention intent.

## S07. Cache identity and admission

Hash the original title/content deterministically (canonical UTF-8 JSON, without rewriting source text). Include catalog-content and pipeline/compiler versions in cache boundaries; version changes must invalidate affected entries.

- Procedure cache: complete compiled source and resolved mappings for the source/version boundary.
- Exact answer cache: exact request identity plus source/version boundary and validated response.
- Semantic answer lookup: same source/version boundary; local similarity proposes candidates, then local compatibility verifies intent, feature/setting, operation, device/app references, negation, and relevant facts including unknowns and protector retention intent.

Ambiguous local compatibility means miss, not an extra hosted verification call. A new fact may miss the answer cache and still hit the procedure cache. Recompute selected preview/applicability for the current request. Never store query-filtered procedures or reuse customer overrides across callers.

Cache only complete validated artifacts. Coordinate identical concurrent misses. Use bounded SQLite storage and bounded in-memory hot caches; configuration and actual bounds must be captured in benchmark manifests. Calibrate similarity thresholds only on development labels and freeze before holdout runs. Cache resets are local benchmark operations, not public API endpoints.

## S08. Errors and non-actionable sources

| Condition | HTTP behavior |
|---|---|
| Valid, source-supported nonempty guide, including manual-only | `200` |
| Malformed request, blank required input | `422` |
| Source genuinely contains no troubleshooting/configuration/service action | `422` |
| Provider/compilation/rendering failure with no usable compatible artifact | `503` |
| Inference admission rejected by capacity/quota | `429` |

Manual-only example: a source with physical force-restart instructions and a duration produces a compliant manual guide without Settings links. Unsupported example: device dimensions and warranty definitions with no procedural or service-directed action. Both examples are fixtures, not extra repair advice to import into unrelated requests.

An unknown article, no catalog match, mismatched complaint, or empty model output is not sufficient to declare the source non-actionable. Model failure on an actionable source is `503`, not `422`. Under the current full-source policy, a mismatched but actionable article still yields its source-backed guide with a separate preview limitation.

Use concise error bodies without source echoes or secrets; official success-schema requirements apply to successful responses, not a fabricated successful error context. Non-success and empty results do not pass the unseen-scenario success test.

## S09. Deadline, model configuration, and deployment

Enforce a 7.5-second application wall-clock budget covering queue/admission, local computation, inference, rendering, validation, and response construction. Reserve the final 0.5 seconds for local completion; hosted calls cannot continue past the remaining inference budget. A socket timeout alone is insufficient. No normal-path retries or automatic remote failover.

Before budget exhaustion, a complete, already validated fallback can be served only if compatible with the current complaint/intent/facts, exact source, catalog, and pipeline versions. Cached procedure material may be used only when current-request processing and validation can finish within budget. Otherwise return `503`. After the total budget expires, start no new fallback work. A truly cold request normally has no fallback.

Measure public-client eight-second latency separately from backend timing. Distinguish exact/semantic answer hits from procedure-only reuse. Record stage durations and executed/skipped stages; do not imply parallel-stage duration sums equal wall time.

Models `gemini-3.1-flash-lite` and `gemini-3.8-flash` remain candidates for normalization and compilation respectively. Verify exact account access, quotas, generation format, and the day-one full workload before retention. Record resolved versions when available and mark unknown metadata explicitly. No billing activation or API call is part of preparing these documents.

Bundle the approved frontend with the backend deployment. Preserve the original templates, use copies for submission, and verify the endpoint externally. Free-tunnel stability and available inference quotas remain deployment risks, not solved capacity claims.

## S10. Safety, privacy, and logs

Treat supplied text as data; it must not override prompts, select arbitrary endpoints, execute code, or alter validation. Materialize only approved catalog URIs. Do not actually invoke masked device links or claim device verification.

Secrets come from local environment configuration, never prompts, command-line arguments, committed files, or benchmark records. Redact provider errors and never log authentication headers. Default logs record request IDs, versions, cache status, timings, and error categories rather than raw complaints/articles. Raw evaluation artifacts contain only approved test data.

Keep databases, caches, temporary files, model downloads, and build outputs under the project boundary. Package required authorized official input copies for reproducibility rather than requiring an unknown parent filesystem at deployment.

## S11. Delivery order and scope control

1. Import read-only inputs; freeze contracts; implement the real API path and independent validators.
2. Run September 21 longest-article cold feasibility and manual-only/error checks, with all relevant caches cleared and stages timed.
3. Complete source/operation correctness, cache guards, and all official inputs; then integrate the real preview.
4. Run sealed comparisons and larger latency measurements; freeze architecture/model configuration.
5. Reproduce from a clean checkout and prepare submission copies inside `submission/`.

Member 4 may develop fixtures/skeletons while the core cold gate runs. Substantial console integration/polish is gated on feasibility. If behind, cut decoration and secondary experiments, not source completeness or independent validation. Do not add general sessions, agents, graphs, or infrastructure to rescue an unmeasured feature.

## S12. Acceptance and change control

EVAL defines release gates and evidence. Documentation or mocked tests alone cannot establish live performance. Preserve the full-source official policy until written organizer clarification changes it; then update PLAN, SPEC, EVAL, pipeline/cache versions, and expected outputs together. Keep whole-source compilation recall even if the official-output interpretation later changes.

Remaining risks: official relevance interpretation, actual model access/quality/latency, free quotas, and public-host availability. Do not present them as resolved. No runtime or production result is claimed by this specification.
