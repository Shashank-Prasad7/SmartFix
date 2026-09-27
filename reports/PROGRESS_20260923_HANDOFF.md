# PRISM Theme 2 progress handoff

Updated: 23 September 2026 (Asia/Calcutta). This file is for continuing the
same task in a new chat. Read `AGENTS.md`, this file, then consult `PLAN.md`,
`SPEC.md`, and `EVAL.md` for the authoritative contract. All new work belongs
under `theme2/`; parent hackathon files are read-only.

## Mission and current status

The user asked for an autonomous production-grade transformation, 100% of the
executable eval suite, a spec audit, refactoring, and a final execution report.
The implementation has reached **22/22 local tests** and **20/20 official-input
offline contract cases**. This is **not** 100% of the full `EVAL.md` release
protocol: independent semantic judging, hosted-model feasibility, public
latency, and submission media remain open. Do not report an official hackathon
score or claim those gates passed.

The code is now in `theme2/src/`, tests in `theme2/tests/`, React/TypeScript UI
in `theme2/frontend/`, and generated official export at
`theme2/submission/results.jsonl`. Old `theme2/codes/` contains only a baseline
README and duplicate data; it is ignored and is not the active package.

## Completed implementation

- Corrected the package layout so `theme2.src` imports work. Installed a
  project-local `.venv` and frontend dependencies. No external API key is
  required for local tests or demo.
- Replaced the six-section/four-step compiler cap with complete source-block
  compilation. Blocks have IDs, exact character offsets, and a coverage ledger.
  No generic Settings action or step is invented when extraction fails.
- Official responses compile all actionable source sections. Preview relevance
  and applicability are separate projections; explicit fact overrides never
  mutate shared cached procedures. The mixed black-screen article retains
  Kids/fingerprint in the official output and excludes them from its preview.
- Resolver checks setting identity and operation before copying action and
  validation metadata from one catalog entry. Touch enable/disable map to
  `DL-0126`/`DL-0125`; Bluetooth/scanning and factory/auto-reset sentinels pass.
  Unknown mappings remain manual/null. Optional local MiniLM is gated by
  `PRISM_MINILM_PATH` and was not available/tested here; BM25 is the default.
- Critical factory reset retains source warnings and an explicit backup
  prerequisite. The synthetic disable-only case does not invent enable.
- Added canonical title/content + catalog/retrieval/pipeline cache identity,
  conservative complaint/fact compatibility, bounded SQLite and hot caches,
  deep-copy cache reads, singleton construction locks, and 64 article locks for
  concurrent miss coordination. Current pipeline version: `source-v2.10`.
- FastAPI serves `/health`, `/v1/troubleshoot`, `/v1/preview`, and the React UI.
  The UI renders untrusted source text as React text, not `innerHTML`.
- Rewrote `tests/run_eval.py` to use a fresh project-local SQLite DB each run,
  validate against both the supplied schema and stricter local checks, verify
  approved catalog URIs and the written export, and record timestamped reports.
- Added a reproducible local loopback benchmark with separate seed, exact, and
  first-exposure paraphrase workloads. Added a source prompt-injection sentinel.
- Replaced a credential-looking value in `.env.example` with a credential-free
  example. Do not copy the old value into reports or chat. If it was live, its
  owner should rotate it.

## Latest measured evidence

The **final** captured logs are:

- `reports/FINAL_TESTS.txt`: `22 passed, 1 warning in 1.01s` (warning is a
  Starlette TestClient deprecation from a dependency).
- `reports/FINAL_LINT.txt`: `All checks passed!` for `src`, `tests`, `scripts`.
- `reports/FINAL_FRONTEND.txt`: strict TypeScript check succeeded and Vite
  built the console in about one second.
- `reports/FINAL_EVAL.txt`: **20/20 PASS**, zero failed, with a fresh cache.
  Each result was validated against the official supplied schema and the
  local FAQ-format/URL checks. Latest run evidence:
  `reports/offline-20260923-105829-3d456b/`.
- `reports/FINAL_LOOPBACK.txt`: fresh isolated service/cache:
  `seed 20/20, p95 58.51 ms`; `exact 250/250 answer hits, p95 29.3 ms`;
  `generated first-exposure paraphrases 180/180 answer hits, p95 34.09 ms`.
  Latest run evidence: `reports/loopback-20260923-105838-dc995a/`.
  These are **local deterministic loopback** timings, not public-network or
  hosted-model latency, and the paraphrases are generated templates rather than
  independently reviewed customer utterances.
- Verified all **11/11 imported official file hashes** and **5/5 protected
  parent-original hashes** against `data/official/manifest.json`.
- A live `uvicorn` smoke test returned 200 for `/health`, `/`, and
  `/v1/preview`; built JS/CSS assets loaded. Browser walkthrough showed the
  mixed-article evidence and off-topic selection. The server process was then
  stopped; an open in-app browser tab may still point to the now-stopped local
  URL.

See `reports/BASELINE.md` for original collection stack traces and counts,
`reports/REMEDIATION.md` for the remediation matrix, and
`reports/RELEASE_STATUS.md` for T01–T22 PASS/PARTIAL/NOT RUN statuses.

## Remaining work and honest limits

1. `EVAL.md` calls for independently labeled full-source actions, relevance,
   applicability, and mapping precision; six additional article cases, fact
   pairs, and 30 adversarial cases. These have not been independently reviewed.
   Do not infer semantic accuracy from schema passes or the compiler ledger.
2. The planned two hosted language stages and cold-path feasibility gate were
   not run: no provider credential/account quota was available. The default
   deterministic path is functional, but model access, two-call fidelity,
   quota-aware `429`, and compatible timeout fallback are unverified/open.
3. The optional local MiniLM path was not tested with a model directory.
   Retrieval confidence and semantic-cache thresholds were not calibrated on
   independent development labels.
4. Inner/cover display fact scoping, the complete conditional/alternative
   matrix, broad prompt-injection/privacy review, restart/version matrix, and
   60 truly cold public observations remain open.
5. Docker is a two-stage frontend/backend build but Docker was not installed
   here, so a clean image build was not verified. `static/app/` is generated
   and ignored; a fresh checkout must build the frontend or use Docker.
6. No public endpoint/external-network check, prescribed deck, five-minute
   video, filled AI disclosure, human review of nine variations, or final Git
   tag was completed. The current Git branch is `master`; `theme2/` is still
   untracked in the parent repository. Stage only project files when ready.

## Exact resume commands (PowerShell, from PRISM repository root)

```powershell
theme2/.venv/Scripts/python.exe -m pytest theme2/tests -q
theme2/.venv/Scripts/ruff.exe check theme2/src theme2/tests theme2/scripts
theme2/.venv/Scripts/python.exe -m theme2.tests.run_eval
theme2/.venv/Scripts/python.exe -m theme2.scripts.benchmark_local
theme2/.venv/Scripts/python.exe -m uvicorn theme2.src.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Then open `http://127.0.0.1:8000/`. For a fresh checkout, follow
`theme2/README.md` to create the local Python environment and build
`theme2/frontend/`. Local `.venv`, `.runtime`, `node_modules`, and built
`static/app` are intentionally ignored.

## Suggested next-chat focus

Start by inspecting `reports/RELEASE_STATUS.md` and the actual official output
for long/mixed articles. Close semantic and release gaps with independent
labels and realistic unfamiliar sources; do not weaken the full-source output
policy or cache compatibility to improve a metric. If provider credentials are
made available, test exact model access and the day-one cold gate before any
performance claim. Keep measured results separate from targets.
