# SmartFix: Source-Grounded Troubleshooting Studio

The service accepts a customer complaint and the full SIIS article supplied with
that request. It compiles every supported source procedure into the official
`ContextDeeplinkResponse` and provides a separate evidence and applicability
preview. No network service or API credential is required for the local demo.
Use the supplied samples or synthetic data. Requests are cached locally and
hosted mode sends text to Gemini; see [privacy and data handling](PRIVACY.md).

## Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/51ba985b-ae5e-4be2-83bd-7339fc85b040" />


The console sends the complaint and supplied article to FastAPI. The pipeline
checks compatible caches, compiles the full article, validates catalog links,
and returns the official response separately from the selected preview.
Gemini is optional and runs only in hosted mode.

## Demo and submission files

- [YouTube demo](https://www.youtube.com/watch?v=dOxAHL3kfXk)
- [SRM Peers of Posts presentation](submission/SRM_Peers_of_Posts_Submission.pptx)
- [AI disclosure working copy](submission/PRISM_Theme2_AI_Disclosure_Working.docx)

The AI disclosure is a working copy and still requires team review, identity
details, representative attestation, and signature.

## What is implemented

- FastAPI `GET /health`, `POST /v1/troubleshoot`, and `POST /v1/preview`.
- `GET /api/samples` for supplied public cases and `GET /api/development-sample`
  for a marked team-authored synthetic foldable case.
- Source blocks with stable IDs and character offsets, full-source compilation,
  a coverage ledger, and a request-specific selection ledger.
- Catalog setting/operation checks with metadata copied from one immutable
  catalog entry. Uncertain and physical actions stay manual; destructive actions
  remain critical.
- Explicit true/false/unknown facts, preview-only overrides, source conditions,
  and separate off-topic and absent-instruction explanations.
- Versioned article and answer caches in bounded SQLite tables and bounded
  in-memory hot caches. Identical concurrent misses share compilation.
- React/TypeScript console served by the same API deployment. It renders text
  through React rather than injecting source text into HTML.
- Optional two-stage Gemini path: hosted technical-query normalization and
  source-constrained JSON procedure ordering. Local checks reject missing,
  changed, or invented source steps and continue to own deeplink metadata.
- Offline contract export using all 20 official canonical queries and nine
  generated variations per query.

The default development pipeline is deterministic and local. The submission
brief requires two LLM stages, so a final deployment must enable and validate
the hosted path. Set `PRISM_LLM_MODE=gemini`, provide `GEMINI_API_KEY` through
the deployment environment, and optionally override `PRISM_NORMALIZER_MODEL`
and `PRISM_COMPILER_MODEL` (defaults in `.env.example`). A fully cold hosted
request calls both models; an exact answer hit calls neither and a compiled
procedure hit skips the second stage. Hosted failures return `429` for quota or
`503` for other unusable results; the service does not silently claim a local
completion as a hosted result. The model IDs and cold-path latency remain
unverified on the team's account.

`PRISM_MINILM_PATH` may point
to an already downloaded `all-MiniLM-L6-v2` directory to warm a dense catalog
index. Without that directory, BM25 and strict compatibility rules handle
catalog lookup. The hosted two-stage model feasibility gate, independent
semantic labels, and public endpoint measurements remain open. The unsigned AI
disclosure working copy is included at
`submission/PRISM_Theme2_AI_Disclosure_Working.docx` and still requires team
review, identity details, representative attestation, and signature. The
presentation and published demo are linked in the submission section below.
Offline contract passes do not establish semantic accuracy or an official score.

## Run locally (PowerShell)

From the repository root:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --workers 1
```

If `py` is unavailable, `uv` can create the environment with Python 3.12:

```powershell
$env:UV_CACHE_DIR = (Get-Location).Path + '\.runtime\uv-cache'
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
```

Open `http://127.0.0.1:8000/`. The quick cases demonstrate the mixed
black-screen source, separately sourced Touch sensitivity operations, and the
team-authored synthetic foldable case. For a repeatable local walkthrough,
open `http://127.0.0.1:8000/?demo=mixed-evidence`,
`?demo=touch-official`, or `?demo=fold-guide`; each runs that case through the
local API and selects the named view.
The console calls `/v1/preview`; the official output is also accessible by
calling `/v1/troubleshoot` directly. The service never invokes a masked Bixby
link on a device.

## Build the console

From `frontend`:

```powershell
pnpm install --store-dir ../.runtime/pnpm-store
./node_modules/.bin/tsc.cmd --noEmit
./node_modules/.bin/vite.cmd build --config vite.config.mjs --configLoader runner
```

The build lands in `static/app`; the backend serves those files. Build
the console before first local launch from a clean checkout. Docker builds it
in its frontend stage.

## Verify and export

From the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/ruff.exe check src tests scripts
.venv/Scripts/python.exe -m tests.run_eval
.venv/Scripts/python.exe -m scripts.run_release_checks
```

`run_eval` gives each run a fresh project-local SQLite cache, writes a 20-line
`submission/results.jsonl` only after all executable checks pass, and records
per-case observations and counts under `reports/`. The generated
variations are structurally unique but still need human semantic review before
submission. Read [SPEC.md](SPEC.md), [PLAN.md](PLAN.md), and [EVAL.md](EVAL.md)
for the stronger acceptance protocol and its current unmeasured gates.

The release runner saves thirteen gate commands, raw stdout/stderr, a source
fingerprint, and a summary in a new `reports/release-*/` directory. It includes
provenance, the local tests, lint, frontend checks, the blank reviewer pack,
development fixtures, official export, clean source-copy check, fresh offline
Python/PNPM dependency install in an isolated source copy, deterministic local
loopback measurement, synthetic cache-scale check, and working-artifact
structure. See [RELEASE_STATUS.md](reports/RELEASE_STATUS.md)
and [FINAL_REPORT.md](reports/FINAL_REPORT.md) for the evidence boundary.
The full runner needs `uv`, `pnpm`, their local offline dependency stores, and
generated submission artifacts. After a fresh clone, use the separate test,
lint, build, and export commands first.

## Submission files

`submission/results.jsonl` is regenerated by the export command above. The 180
generated query variations still need human semantic review. The uploaded
12-slide presentation is `submission/SRM_Peers_of_Posts_Submission.pptx`.
The AI disclosure at `submission/PRISM_Theme2_AI_Disclosure_Working.docx` is a
working copy: team identity, representative attestation, and signature still
require review and completion.

The demo video is published at
[youtube.com/watch?v=dOxAHL3kfXk](https://www.youtube.com/watch?v=dOxAHL3kfXk).
The project also includes a local video builder. To generate a new local copy,
start the API, ensure ffmpeg is on PATH, then run it with Python and Pillow:

```powershell
python scripts/build_demo_video.py --release-run reports/<release-run-id>
```

Replace `<release-run-id>` with a verified passing directory name. Build the
deck from the same release evidence with:

```powershell
python scripts/build_submission_deck.py --release-run reports/<release-run-id>
```

The disclosure builder is
`scripts/build_ai_disclosure.py`. The builders need `python-pptx`,
`python-docx`, Pillow, and ffmpeg/ffprobe as applicable. Team name, college,
members, email, GitHub URL,
representative attestation, and signature require the team's actual details.

## Container

```powershell
docker build -f Dockerfile -t prism-theme2 .
docker run --rm -p 8000:8000 prism-theme2
```

The Docker build expects the repository root as its build context and runs one
worker. Runtime state stays under `.runtime`. The official input files in
`data/official/` are read-only and tracked by `data/official/manifest.json`.
For a hosted deployment, pass `PRISM_LLM_MODE=gemini` and `GEMINI_API_KEY`
through the container environment or secret manager, then run the live cold
path, quota, and public latency checks described in `EVAL.md`.
