# Theme 2 release protocol status · 24 September 2026

Last full local release evidence before repository cleanup: `release-20260924-200037-a92bc0/summary.json` (13/13 local
gates passed). `PASS` means the named deterministic check ran; `PARTIAL` means
some checks ran but the full EVAL requirement remains open. `BLOCKED` identifies
an external input needed for the case. The statuses are **not** a competition
score or an independent semantic quality assessment.
Run directories are kept in the local workspace and excluded from Git; this
file records their measured counts and limits for repository readers.

The pre-PR cleanup added an opt-in, two-stage Gemini adapter after that release
run. Its normalization, source-constrained JSON structuring, cache skips, and
credential guard pass mocked tests. The subsequent PRISM/privacy review adds
request-error privacy and admission-deadline regressions; the current suite
passes 112/112. See [PUSH_REVIEW.md](PUSH_REVIEW.md) for the final local review.
No live provider call or fresh full release run is included in this status.

| EVAL case | Status | Evidence and remaining boundary |
|---|---|---|
| T01 trusted inputs | PASS | `provenance`: 11/11 imported hashes and sizes, 5/5 protected parent originals, 6/6 nested entries. Generated work is under `theme2/`. |
| T02 API contract | PASS | Tests cover exact health shape, malformed/blank 422, official success schema, preview separation, and status headers. |
| T03 full source recall | PARTIAL | `official_export`: 20/20 valid nonempty contract cases; source ledger/offset checks pass. A browser-discovered linked Touch paragraph was split into its distinct manual and catalog actions; independent action inventory, binding, and recall are unmeasured. |
| T04 strict output mutations | PASS | Mutation tests reject title/description/goal/score/list/extra-field violations, including NaN and prohibited fragments. |
| T05 prohibited fragments | PASS | Sanitizer and actual mixed-article regressions, structural mutation tests, and full official export validation pass. This is tested output only. |
| T06 exact operation mapping | PARTIAL | Reversal, Bluetooth/scanning, factory/auto-reset, partial-overlap wrong-link, and same-paragraph manual/catalog split regressions pass; independent mapping precision remains unmeasured. |
| T07 validation metadata | PASS | All 578 catalog entries audited; same-entry actionable/validation metadata checked, including incomplete URI/key-only and absent-validation cases. |
| T08 manual and dummy boundaries | PASS | Physical-only 200 manual/null and genuine unmatched Settings screen dummy cases pass; unrelated/ambiguous mappings stay manual. |
| T09 touch branches and conditions | PASS | Both source-backed enable/disable branches map separately to DL-0126/DL-0125; separate manual actions and unknown conditions remain visible; retention unknown/contradictory states tested. Local capture has 9 procedures and 12 actions. |
| T10 absent inverse | PASS | Labeled synthetic disable-only source never invents enable; preview distinguishes absent instruction. |
| T11 mixed article relevance | PASS | Official response retains all five local mixed-article procedures; preview selects two and flags three off-topic in a local API capture. Independent relevance judgment is still part of T03/T21. |
| T12 scoped display facts | PARTIAL | Inner/cover, visible/touch, alternative input, HDMI, unknown source conditions, and 6/6 authored fact pairs pass local checks; independent applicability matrix is unmeasured. |
| T13 destructive prerequisites | PASS | Tests check reset last-resort, erasure, backup prerequisite, critical category, order, and wrong destructive mapping. |
| T14 guarded paraphrases | PARTIAL | 30/30 authored adversarial cache cases pass; 180 generated first-exposure variants hit locally. Genuine human-reviewed paraphrase meaning and compatibility rate are unmeasured. |
| T15 version/source invalidation | PASS | Restart/source/catalog/pipeline changes, changed facts, corrupted procedure recovery, bounded eviction, and post-store deadline discard tested deterministically. A late failed attempt leaves no new answer/procedure; a late semantic write preserves its valid seed. |
| T16 concurrency/restart | PASS | Concurrent identical misses, isolation across callers, and persistence/version boundaries pass deterministic tests. |
| T17 error semantics | PARTIAL | Manual 200, descriptive-only 422, actionable compile failure 503, 3/3 team-authored unfamiliar article contract cases, and mocked transport failures pass. Real hosted-model failure matrix is unavailable. |
| T18 timeout fallback | PARTIAL | Mocked no-compatible-artifact timeout maps to 503; the pipeline reserves 0.5 seconds and deterministic post-store deadline regressions reject late cache admission. Real hosted timeout, cancellation, public wall-clock behavior, and compatible validated fallback workload remain unverified. |
| T19 quota/admission | PARTIAL | Injected `AdmissionRejected` maps to 429 without a repair call; actual provider quota/admission and cold-path behavior are untested. |
| T20 injection/privacy | PARTIAL | Sentence-level source injection regressions and no-secret/source-output checks pass; broader adversarial privacy review has no independent audit. |
| T21 sealed unfamiliar sources | BLOCKED | Three independently supplied sealed articles/fact pairs and two independent reviewer labels are unavailable. Prepared blank sheets exist under `data/annotations/review_pack/`; no holdout was tuned. |
| T22 release artifacts | PARTIAL | Local console, 20-line export, clean source-copy, isolated fresh offline Python/PNPM install, 12-slide working deck, working disclosure, 95.97-second local video, and provenance checks pass. Docker, public endpoint, visual Office QA, reviewed variations, team signature, final Git commit/tag are pending. |

## Measurement boundary and external inputs

The latest local loopback run `loopback-20260924-200110-629a05` used a fresh SQLite
cache and deterministic backend: 20/20 seed successes p95 42.6 ms;
250/250 exact answer hits p95 26.23 ms; 180/180 first-exposure generated
variation hits p95 32.48 ms; 70/70 separately labeled repeated variations hit
at p95 26.8 ms. The combined 500/500 cached observations had p95 31.74 ms;
the 70 repeats are excluded from the first-exposure cache-hit denominator.
The separate synthetic cache-scale run `cache-scale-20260924-200121-5eb7ea`
wrote 10,001 keys to a 10,000-entry bound and hit 200/200 sampled post-restart
lookups at p95 0.099 ms. These
measurements do not cover hosted inference,
public-network latency, fully cold public observations, or semantic correctness
of the variations. Only team-authored fixtures and deterministic regressions
were judged locally. No model tokens, provider charges, or official score were
measured.

Specific gates still `NOT RUN`: real hosted-model calls and two-stage scoring
(account access/quota and live behavior unverified); Docker build and container launch (no Docker
executable); 60 fully cold public requests and external-network p95 (no approved
public endpoint). The independent semantic review is `BLOCKED` on sealed cases
and two human reviewers. Visual Office QA was attempted but remains `PARTIAL`
because both render routes failed; exact errors are in `OFFICE_DOCX_RENDER.txt`
and `OFFICE_PPTX_RENDER.txt`.

The next gates require provider credentials with known tier/quota, independent
human reviewers and sealed cases, and a team-approved public host/tunnel.
Publication and billing require authorization. Visual Office review requires a
working renderer or a team workstation; this session's `soffice.exe` lookup and
PowerPoint COM render both failed. The working deck and disclosure are drafts.
