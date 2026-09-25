# Remediation matrix · 23 September 2026

| Gap / baseline observation | Root cause | Remediation and evidence |
|---|---|---|
| Initial baseline: 0 tests collected, 3 collection errors | `python` absent from PATH; code was under `theme2/codes` although tests imported `theme2.src`; FastAPI TestClient lacked `httpx2`. After moving the package, the remaining import error was an undeclared `sentence_transformers` dependency. | Project-local virtual environment, corrected package layout, declared dev transport, and local-only optional MiniLM. Current suite collects and passes 17 tests. |
| Original paraphrase test failed after collection was fixed | It required a semantic hit despite a different article title/hash and no compatible seed. That contradicted the source boundary in SPEC S07. | Corrected the fixture to seed the same article; added changed-source and changed-operation guard assertions. |
| Source omission and invented fallback | Compiler limited sections to six, steps to four, conditioned compilation on query, and fabricated a generic Settings instruction when extraction failed. | Whole-article source blocks, no section/step cap, source ledger, explicit non-actionable error, and complete official renderer. Offline contract export covers 20/20 official queries. Semantic recall remains unmeasured without independent labels. |
| Wrong or unsupported catalog links | Generic text score could select a different setting or operation; weak matches became a dummy link. | Setting and operation compatibility checks, immutable same-entry materialization, manual/null on uncertainty. Touch enable/disable and Bluetooth/scanning sentinels pass. |
| Legacy sanitizer invented recovery content | It inserted a generic Settings step when sanitization removed all steps and attached a dummy link to any automatic action without catalog evidence. | Sanitization now rejects unusable steps or unsupported automatic actions. The old dummy-link test was updated to enforce the source-boundary rule. |
| Unsafe answer reuse | Old semantic cache only checked embedding similarity inside an article and did not compare facts, intent, device, or operation; storage was unbounded and unversioned. | Canonical source+catalog+pipeline hashes, conservative complaint compatibility, bounded SQLite/hot caches, deep-copy reads, and coordinated concurrent misses. |
| Preview missed its core contract | It returned only a normalized object and trace, with shared-normalizer fact mutation risk. | Separate selection, applicability, evidence, and trace projection; overrides are applied to a request-local fact copy. Mixed-source off-topic and touch unknown/false/true sentinels pass. |
| Frontend could render source text as HTML | Baseline static JavaScript interpolated API values into `innerHTML`. | React/TypeScript console renders source as text and is served from the backend. TypeScript check and Vite build pass. |
| Credential-like value in `.env.example` | An example configuration included a concrete provider token. | Replaced with credential-free local configuration and searched project files for additional matching tokens. If that value was live, it should be rotated by its owner. |

## Evidence boundary

The offline export validates the supplied schema, stricter local contract, URL
policy, and query coverage. It does not measure independently judged source
accuracy, live hosted-model behavior, public endpoint latency, or a hackathon
score. Those gates remain open under `EVAL.md`.
