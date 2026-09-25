# PRISM Theme 2 progress handoff

Updated: 25 September 2026 (Asia/Calcutta). Continue the active Theme 2 goal
from this state. Read `AGENTS.md`, `README.md`, `PLAN.md`, `SPEC.md`, `EVAL.md`,
and `reports/RELEASE_STATUS.md`. The previous 23 September handoff is preserved
at `reports/PROGRESS_20260923_HANDOFF.md`; its logs remain in `reports/`.

## Current boundary

The local deterministic pipeline and working submission copies are implemented.
The last complete local gate before repository cleanup is `reports/release-20260924-200037-a92bc0/`:
**13/13 checks passed** with source fingerprint
`09555dc394fc9d02cf42efc842428ffcc7a22bb3077101edd2ca58b4d1863c23`.
It includes **105/105 tests**, **20/20 supplied-query contract cases**, 3/3
team-authored unfamiliar article contract cases, 6/6 authored fact pairs, a
30-case adversarial cache regression, a clean source-copy test/export, and a
fresh offline Python/PNPM dependency install in an isolated source copy.
These checks do **not** establish independent semantic accuracy, hosted-model
feasibility, public latency, or an official competition score.

The official output still renders the full article. The preview separately
selects relevant procedures and applicability. No supplied schema, source,
catalog, or protected parent file was changed, and no benchmark denominator
was reduced. The added 70 repeated variations are reported separately.

## Completed since the previous handoff

- Tightened setting and operation identity and same-entry validation metadata;
  audited all 578 catalog entries and tested wrong-link families and the narrow
  dummy boundary. Uncertain mappings remain manual/null.
- Improved source compiler handling for scoped inner/cover facts, alternate
  input/HDMI language, reset prerequisites and warnings, same-block conditional
  alternatives, mixed Tips sections, and sentence-level prompt injection.
  A browser walkthrough exposed a catalog-linked paragraph containing manual
  instructions before and after the Touch sensitivity action. The compiler now
  splits those instructions and retains unknown source conditions for manual
  confirmation; a focused regression covers this. The current local capture
  has 9 Touch procedures and 12 actions with separate DL-0126/DL-0125 links.
  Full-source official rendering and source offsets remain intact.
- Tightened cache source/version/catalog identity, restart behavior, current
  query scoring on semantic hits, cross-caller preview isolation, and corruption
  recovery. Fixed second-resolution disk-eviction ambiguity and eliminated the
  full-table eviction scan on every write. Current cache version is `source-v2.23`.
- Added a deadline check, internal stage timings, mocked timeout/429 error
  paths, and a truthful preview trace showing **zero hosted model calls**.
  A deterministic post-store deadline regression exposed late cache admission:
  a request could fail its budget after writing an answer. The pipeline now
  reserves 0.5 seconds for completion and discards answer/procedure writes from
  that failed attempt while holding its article lock. A second regression checks
  that a late semantic-hit write leaves the valid seed intact. These are local
  failure-path tests, not real hosted timeouts or a public deadline guarantee.
- Added three team-authored development articles, six paired fact cases, 30
  adversarial cache pairs, a reproducible development runner, and blank
  independent-review sheets. No engine-authored labels are called independent.
- Added provenance, clean source-copy, fresh offline dependency install,
  synthetic 10,000-entry cache scale, and 13-gate release scripts. Working
  deck, disclosure, result export, and a silent captioned 95.97-second local
  API storyboard video are under `submission/`. The video evidence manifest is
  `submission/DEMO_CAPTURE.json`. The deck and video cite passing run
  `release-20260924-185306-2645c4`; the latest run revalidated both. The UI
  has three quick cases and optional local `?demo=` walkthrough URLs.

## Latest measured evidence

From `reports/release-20260924-200037-a92bc0/` (local run logs are excluded from Git):

- Provenance: 11/11 imported hashes and sizes, 5/5 protected parent originals,
  and 6/6 nested archive entries matched.
- Pytest: `105 passed, 1 warning in 2.45s`; the warning is a Starlette TestClient
  dependency deprecation. Ruff, strict TypeScript, and Vite build passed.
- Offline export: `20/20 passed; 0 failed`; fresh isolated cache; exact supplied
  schema and stricter local FAQ/catalog checks; 20 JSONL lines.
- Isolated fresh offline dependencies: new Python environment, Python package
  install, PNPM install, TypeScript, Vite, tests, and export all exited 0;
  `reports/fresh-deps-20260924-200052-775eeb/`. Docker was NOT RUN.
- Local loopback, deterministic backend: seed 20/20 success p95 42.6 ms;
  exact repeats 250/250 answer hits p95 26.23 ms; first-exposure generated
  variants 180/180 answer hits p95 32.48 ms; separately labeled 70/70 repeated
  variations p95 26.8 ms. The combined cached workload is 500/500 answer
  hits p95 31.74 ms. The 70 repeats are excluded from the first-exposure rate.
  These are **not** hosted or public measurements; variants are not human reviewed.
- Synthetic cache scale: 10,001 writes retained 10,000 disk and 512 hot entries;
  200/200 post-restart sampled lookups hit, p95 0.099 ms. This is storage and
  lookup evidence, not semantic accuracy or request latency.
- Working artifacts: 12 template slides, disclosure XML present, 95.97-second
  MP4, three local API captures, and 20 export lines passed structural checks.
  The video frames were locally inspected; Office visual render was unavailable.

The earlier 22/22 tests and 20/20 contract result remain historical prior
evidence; the current result above supersedes them. Inspect each release gate's
`*.stdout.txt`, `*.stderr.txt`, and `summary.json` for exact commands and output.

## Remaining requirements and external dependencies

1. **Independent judgment:** two human reviewers must label full-source
   actions, relevant preview inventory, applicability, mapping precision,
   conditions/warnings, and variation meaning. Blank sheets and protocol are
   ready in `data/annotations/`. Three sealed unfamiliar articles and sealed
   fact pairs are needed for T21; do not tune on them.
2. **Hosted model gate:** no provider credential/account quota was available.
   The production path remains deterministic and local; the planned two hosted
   language stages, account model-ID resolution, token/cost accounting, real
   timeout/quota behavior, and 60 fully cold public observations are untested.
   Only deterministic mocked failure paths were exercised. Do not paste a key
   into chat or activate billing without authorization.
3. **Deployment:** Docker was not available; a public endpoint, external-network
   health check, and public p95 need a team host/tunnel and publication approval.
   No endpoint has been published and no billing was activated.
4. **Final submission review:** team/college/member details, GitHub URL,
   disclosure attestation and signature, slide/Word visual QA, and review of
   nine variations per query are pending. LibreOffice `soffice.exe` was absent;
   PowerPoint COM render failed with Windows error `80070520`. The working video
   is a captioned local API storyboard without audio, not a live screen recording.
   The final reviewed Git commit and `PRISM_GENAI_HACKATHON_Y2026` tag remain
   pending. This local workspace is a staging area; the project is intended
   for a pull request into the teammate's repository. Keep that PR scoped to
   `theme2/` unless the destination repository needs root-level integration.

Do not mark the goal complete, report 100% EVAL completion, or call local
loopback a public/hosted score. `reports/FINAL_REPORT.md` records the current
decision, exact commands, metrics, launch steps, and material limits.

## Reproduce from the PRISM parent directory

```powershell
theme2/.venv/Scripts/python.exe -m theme2.scripts.run_release_checks
theme2/.venv/Scripts/python.exe -m uvicorn theme2.src.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. For a true clean checkout, first install
dependencies and build the frontend as shown in `README.md`.
