# SmartFix: Guided Troubleshooting Studio

Samsung PRISM GenAI Hackathon Theme 2. The application accepts a complaint and a supplied SIIS article, compiles source-grounded troubleshooting steps, and returns the required response through FastAPI. A React console provides a separate evidence and applicability preview.

## Status

The API, console, guarded cache, tests, and Dockerfile are implemented. The last complete local release run passed 13/13 checks and 105 tests. The current local PR preparation passes 112 tests, including mocked hosted stages and privacy regressions, plus Ruff, a fresh frontend install/build, a 20/20 deterministic export, and official-input provenance. These results are local contract evidence; hosted feasibility, public latency, and independent semantic quality still require measurement. See the [PRISM and privacy review](theme2/reports/PUSH_REVIEW.md).

The submission brief requires two language stages. Set `PRISM_LLM_MODE=gemini` and provide `GEMINI_API_KEY` through the deployment environment to use the implemented normalization and procedure-structuring stages. Actual account access, quota, source quality, and cold latency remain unverified. The team also needs independent semantic review, human review of generated query variations, a Docker and public-endpoint check, and final submission artifact review and sign-off. See [Theme 2 release status](theme2/reports/RELEASE_STATUS.md) and [evaluation protocol](theme2/EVAL.md).

## Run locally

Use Python 3.12, Node.js 24, and pnpm. From the repository root:

```powershell
py -3.12 -m venv theme2/.venv
theme2/.venv/Scripts/python.exe -m pip install -r theme2/requirements-dev.txt
Push-Location theme2/frontend
pnpm install --frozen-lockfile
pnpm build
Pop-Location
theme2/.venv/Scripts/python.exe -m pytest theme2/tests -q
theme2/.venv/Scripts/python.exe -m uvicorn theme2.src.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. See [theme2/README.md](theme2/README.md) for API endpoints, export steps, Docker commands, and submission artifact generation. The official sample inputs live under `theme2/data/official/` with recorded hashes. Local environments, caches, run logs, and unfinished submission files are excluded from Git.
