# PRISM Theme 2 execution report

Date: 24 September 2026 (Asia/Calcutta). This records the named local release
run; see `RELEASE_STATUS.md` for the later local run. It is not a final
competition submission or official score.

## Decision

The deterministic Theme 2 API, evidence console, protected source/catalog
provenance, review pack, and working submission copies are ready for team review.
The release run recorded here is
`release-20260924-185306-2645c4/summary.json`: **13/13 gates passed** with
source fingerprint
`e45dc467e17c419d9b9723fa2895b9567fc388ee352f3591200772f761ae6fe4`.
The 20 supplied queries produced locally valid, nonempty official responses.
Independent semantic quality, live hosted inference, public latency, and final
submission gates remain unverified. No official competition score is claimed.

## What changed

The service compiles the full supplied article into source-referenced procedures
and renders all supported source actions in the exact official success schema.
The separate preview selects relevant procedures, shows explicit three-state
facts and applicability, and exposes source offsets, catalog IDs, and trace
timings. The resolver now requires setting and operation identity and copies
action/validation metadata from the same immutable catalog entry; uncertain
links stay manual/null. Conditional touch branches, scoped foldable-display
facts, reset warnings/prerequisites, mixed-article topics, and prompt-injection
sentences have focused regressions. Browser QA of the official Touch article
exposed manual instructions on either side of a linked setting instruction in
one paragraph. The compiler now splits these into distinct actions and keeps
an unknown source condition visible for manual confirmation. The current local
capture reports 9 Touch procedures and 12 actions, with DL-0126 and DL-0125
only on their respective source-backed setting operations.

The cache uses the full article, catalog digest, and `source-v2.23` pipeline
version as identity. Changed source, version, operation, or relevant fact cannot
silently reuse an incompatible answer. Disk eviction now uses nanosecond
timestamps with deterministic tie order and trims only after the configured
bound is exceeded. A focused restart regression checks oldest eviction and
newest retention. Both hot and disk caches remain bounded. Two deterministic
deadline regressions found and closed a late-admission race: the pipeline now
reserves 0.5 seconds for completion and discards newly stored artifacts from an
attempt that crosses its completion deadline while holding the article lock.
A late semantic-hit write preserves its prior valid seed. These mocked slow
storage paths do not establish real hosted timeout or public latency behavior.

All generated work is under `theme2/`. The full official-output policy, supplied
schema, 11 imported sources, 578-entry catalog, and protected parent inputs
remain unchanged. A provenance command checked 11/11 imported hashes and sizes,
5/5 protected parent originals, and 6/6 nested archive entries.

## Exact local verification

Run from the PRISM parent directory. The one-command release gate records each
command, exit code, elapsed time, stdout, and stderr in its run directory:

```powershell
theme2/.venv/Scripts/python.exe -m theme2.scripts.run_release_checks
```

The completed run returned exit `0` and:

```text
provenance: PASS
tests: PASS
lint: PASS
typescript: PASS
frontend_build: PASS
review_pack: PASS
development: PASS
official_export: PASS
clean_copy: PASS
fresh_dependencies: PASS
loopback: PASS
cache_scale: PASS
submission_artifacts: PASS
RELEASE LOCAL SUMMARY: 13/13 PASS, export lines=20
```

Its exact component commands were:

```powershell
theme2/.venv/Scripts/python.exe -m theme2.scripts.verify_provenance
theme2/.venv/Scripts/python.exe -m pytest theme2/tests -q
theme2/.venv/Scripts/ruff.exe check theme2/src theme2/tests theme2/scripts
# From theme2/frontend:
./node_modules/.bin/tsc.cmd --noEmit
./node_modules/.bin/vite.cmd build --config vite.config.mjs --configLoader runner
# Back at PRISM root:
theme2/.venv/Scripts/python.exe -m theme2.scripts.prepare_review --check
theme2/.venv/Scripts/python.exe -m theme2.scripts.run_development
theme2/.venv/Scripts/python.exe -m theme2.tests.run_eval
theme2/.venv/Scripts/python.exe -m theme2.scripts.verify_clean_copy
theme2/.venv/Scripts/python.exe -m theme2.scripts.verify_fresh_dependencies
theme2/.venv/Scripts/python.exe -m theme2.scripts.benchmark_local
theme2/.venv/Scripts/python.exe -m theme2.scripts.benchmark_cache_scale
theme2/.venv/Scripts/python.exe -m theme2.scripts.verify_submission_artifacts
```

Observed outputs and evidence:

| Gate | Output | Evidence |
|---|---|---|
| Provenance | 11/11 imported; 5/5 protected originals; 6/6 archive entries | `release-20260924-185306-2645c4/provenance.stdout.txt` |
| Tests | `100 passed, 1 warning in 2.29s` | `tests.stdout.txt`; warning is a Starlette TestClient dependency deprecation |
| Ruff | `All checks passed!` | `lint.stdout.txt` |
| TypeScript and Vite | strict type check exit 0; Vite built 28 modules in 782 ms | `typescript.stdout.txt`, `frontend_build.stdout.txt` |
| Reviewer pack | `9/9 files match current inputs` | `review_pack.stdout.txt`; these are blank sheets, not judgments |
| Development | 3/3 team-authored unfamiliar article contract cases; 6/6 authored fact pairs | `development.stdout.txt`, `development-20260924-185312-ad009d/` |
| Official export | `20/20 passed; 0 failed`; 20 JSONL lines | `official_export.stdout.txt`, `offline-20260924-185314-240643/` |
| Clean source copy | tests exit 0, export exit 0, 20 lines | `clean_copy.stdout.txt`, `clean-copy-20260924-185314-815d81/` |
| Fresh dependencies | new offline Python environment, Python/PNPM install, TypeScript, Vite, tests, and export all exit 0; 20 lines | `fresh_dependencies.stdout.txt`, `fresh-deps-20260924-185318-5728d0/` |
| Loopback | 20/20 seed requests and 500/500 cached observations succeeded across separately reported workloads | `loopback.stdout.txt`, `loopback-20260924-185331-1aed0f/` |
| Cache scale | 10,001 synthetic writes, 10,000 disk rows, 512 hot rows; 200/200 sampled post-restart lookups | `cache_scale.stdout.txt`, `cache-scale-20260924-185342-9ffe11/` |
| Working artifacts | 12-slide PPTX, disclosure XML, 95.97-second MP4, 3 case captures, 20 export lines | `submission_artifacts.stdout.txt`, `submission/DEMO_CAPTURE.json` |

The clean-copy check uses the existing virtual environment. The separate fresh
dependency check creates an isolated environment from a source copy and installs
Python and PNPM dependencies from local caches without network access. Docker
was not present on this host, so `docker build` was **NOT RUN**.

## Measurements and denominators

The local loopback runner starts an isolated ready service with an empty SQLite
cache, sends each of the 20 supplied canonical requests once, then 250 exact
repeats, 180 first-exposure mechanically generated variations, and 70 separately
labeled repeated variations. Its monotonic nearest-rank p95 and sample counts
are in `metrics.json`:

| Workload | Success | Answer hits | p95 |
|---|---:|---:|---:|
| Seed | 20/20 | 0/20 | 41.6 ms |
| Exact repeat | 250/250 | 250/250 | 16.41 ms |
| First generated variation | 180/180 | 180/180 | 30.91 ms |
| Repeated generated variation | 70/70 | 70/70 | 16.33 ms |
| Combined cached workload | 500/500 | 500/500 | 30.06 ms |

The 180 first-exposure variations have not been reviewed for genuine paraphrase
meaning. The 70 repeats are excluded from their hit-rate denominator. The
timings are local Windows loopback for a deterministic backend; they are **not**
public-network, hosted-model, or fully cold provider latency. Successful schema
and FAQ checks do not measure grounded-step precision, full-source action
recall, preview relevance, mapping precision, or applicability correctness.
Those metrics are intentionally unreported until independent labels exist.

The separate synthetic cache-scale run wrote 10,001 keys into a 10,000-row
disk bound in 40,317.89 ms, retained the newest and evicted the oldest after
restart, and hit 200/200 sampled disk lookups at p50 0.04 ms, p95 0.083 ms,
maximum 0.518 ms. Configured hot bound was 512. This tests storage/lookup in
one process; it is not 10,000-scenario semantic accuracy, provider capacity,
or complete request latency. The first pre-optimization scale attempt was
interrupted after over a minute of repeated eviction scans; no passing metric
is claimed from that attempt.

The 30 authored adversarial cache opportunities and six authored fact pairs
pass deterministic regressions, but they are development assertions by the
implementation team. The independent-review materials include 11 supplied
articles, 20 public queries, three development articles, six development fact
pairs, 30 adversaries, and 180 generated variations. Reviewer A/B sheets remain
blank; no engine-authored expectation has been counted as independent judgment.

## Comparison and hosted-model gate

The earlier extraction-conditioning comparison was inspected without making a
provider call:

```powershell
theme2/.venv/Scripts/python.exe experiments/theme2_model_comparison.py --rows row_21,row_9 > theme2/reports/COMPARISON_DRY_RUN.json
```

Output: `mode=dry_run`, `network_calls=0`, two articles, 578 catalog entries per
arm, six planned model calls. Source-only prompts were 200,536 and 194,383
characters. This is a workload plan, not an actual model or architecture
comparison. No superiority, token cost, quota, source-fidelity gain, or live
latency is claimed. No provider key/account quota was available in the session.
The active API path is deterministic; preview trace truthfully reports zero
hosted calls. Mocked timeout and quota/admission tests verify local 503/429
handling only. Actual model IDs, two-stage hosted fidelity, compatible warm
fallback, real provider timeout/429, and the fully cold public gate remain open.

## Working submission artifacts

| Artifact | Current status |
|---|---|
| `submission/results.jsonl` | 20 locally validated lines; nine generated variations per canonical query require human review. |
| `submission/PRISM_Theme2_Submission_Working.pptx` | Supplied 12-slide template filled with bounded evidence; team/college/member/GitHub details and visual review pending. |
| `submission/PRISM_Theme2_AI_Disclosure_Working.docx` | Supplied form filled with AI-use details; actual representative attestation/signature and visual review pending. |
| `submission/PRISM_Theme2_Local_Demo_Working.mp4` | Silent, captioned 95.97-second local API storyboard; three observed case captures and release metrics in `DEMO_CAPTURE.json`. It is not a live UI screen recording. |

The working deck and video cite the passing
`release-20260924-185306-2645c4` run, which reported 100 tests and 20/20
contract cases. The artifacts were rebuilt after that run and passed focused
structural verification; the release's artifact gate verified their preceding
copies. The code and export were unchanged by rebuilding the media.

The current deck and video were built from that passing run with:

```powershell
python theme2/scripts/build_submission_deck.py --release-run reports/release-20260924-185306-2645c4
python theme2/scripts/build_demo_video.py --release-run reports/release-20260924-185306-2645c4
theme2/.venv/Scripts/python.exe -m theme2.scripts.verify_submission_artifacts
```

Outputs: `DECK: 12 template slides filled`, `DEMO: ...; 96 seconds; six
captioned slides; no audio`, and `WORKING ARTIFACTS: 12 template slides,
disclosure text present, 95.97s demo, 3 local case captures, 20 export lines`.

PPTX and DOCX ZIP structures passed checks. Visual Office rendering was
attempted and failed on this host: the bundled DOCX renderer reported
`LibreOffice soffice.exe was not found on PATH`, and PowerPoint COM returned
`80070520 A specified logon session does not exist`. Exact errors are retained
in `OFFICE_DOCX_RENDER.txt` and `OFFICE_PPTX_RENDER.txt`. A team workstation
must visually inspect both files before submission. The video frames were
opened and inspected locally; `ffprobe` measured 95.97 seconds, under the
five-minute limit.

This local workspace is a staging area for a pull request into the teammate's
repository. No reviewed integration commit or final
`PRISM_GENAI_HACKATHON_Y2026` tag has been created.
No public endpoint was published and no billing was activated.

## Launch and demo

From a fresh checkout that contains `theme2/` and an authorized local Python
3.12 environment, follow `theme2/README.md` to install
`theme2/requirements-dev.txt` and build `theme2/frontend/`. From PRISM root:

```powershell
theme2/.venv/Scripts/python.exe -m uvicorn theme2.src.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. The quick cases show the supplied mixed article,
the two Touch sensitivity operations, and a marked synthetic foldable source.
For a repeatable walkthrough, open `/?demo=mixed-evidence`,
`/?demo=touch-official`, and `/?demo=fold-guide`. The UI displays the selected
guide, complete official response, evidence, cache decision, and stage trace.
The API endpoints are `GET /health`, `POST /v1/troubleshoot`, and
`POST /v1/preview`. The service does not operate a real device.

## Release blockers and input needed

`reports/RELEASE_STATUS.md` records each T01–T22 status. The open gates need:

1. Two independent reviewers and three sealed unfamiliar article families plus
   sealed fact pairs. Give reviewers the blank sheets in
   `data/annotations/review_pack/` and use `data/annotations/REVIEW_PROTOCOL.md`.
   Freeze the candidate before revealing holdout labels.
2. Authorized provider credentials with model access and quota details to test
   the two hosted stages, true cold requests, timeout/fallback, 429, calls,
   tokens, actual charges, and fair baseline comparison. No billing or paid
   requests should begin without separate authorization.
3. A team host/tunnel and explicit publication approval for an external API
   check and public latency measurements. The isolated source-copy dependency
   installation passed; Docker image build and runtime remain untested because
   Docker is unavailable here.
4. Actual team details, GitHub destination, representative disclosure sign-off,
   human review of variations, Office visual QA, and approval of the final
   commit/tag and media before submission.

The current result is a working local candidate with transparent partial EVAL
coverage, ready for those external gates. It is not a claim of full EVAL
completion or production deployment.
