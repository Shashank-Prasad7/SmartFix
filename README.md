# SmartFix: Smart Guided Troubleshooting Engine
### Samsung PRISM GenAI Hackathon 3.0 — Theme 2

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![Scoring Gates](https://img.shields.io/badge/Scoring%20Gates%20(G2--G5)-100%25%20PASS-success.svg)](#scoring-gates-validation)

SmartFix is a high-performance guided troubleshooting engine that transforms natural-language device complaints and raw SIIS (Samsung Internal Knowledge Store) articles into structured, verified troubleshooting guides enriched with Galaxy Settings deeplinks.

---

## 🚀 Key Features & Highlights

- **FastAPI REST Service**: Production endpoints `GET /health` (`{"status": "ok"}`) and `POST /v1/troubleshoot` conforming strictly to the official `ContextDeeplinkResponse` schema.
- **Interactive Web Demo Console**: Glassmorphic single-page web console served at `http://localhost:8000/` for interactive testing across all 20 canonical scenarios.
- **Two-Stage Agentic Pipeline**:
  - **Stage 1 (Complaint Normalization)**: Standardizes user intent, technical complaint, feature area, and extracted device facts.
  - **Stage 2 (SIIS Procedure Compiler)**: Chunks and compiles SIIS knowledge articles into verified actions and steps without inventing ungrounded advice. Supports live Google Gemini LLM reasoning with deterministic offline fallback.
- **Dual-Index Deeplink Resolver**: Hybrid lexical BM25 + dense sentence-transformers (`all-MiniLM-L6-v2`) indexing over all 578 Galaxy Settings deeplinks, with operation disambiguation (enable vs disable, Bluetooth vs Bluetooth scanning, Factory Reset vs Auto Reset) and validation deeplink copying.
- **Multi-Tier Latency & Caching ($\le 300\text{ ms}$ p95 target)**:
  - **Tier 1 (Exact Answer Cache)**: In-memory hash lookup returning in **`0.04 ms`**.
  - **Tier 2 (Semantic Paraphrase Cache)**: Cosine similarity over query embeddings returning in **`23.43 ms`** ($\ge 80\%$ hit rate target).
  - **Tier 3 (Compiled Procedure Cache)**: Instantaneous reuse of compiled procedures across varying queries for the same article.
- **Scoring Gates Validation (100% Pass Rate)**:
  - **Gate G2**: `GET /health` returns `{"status": "ok"}`.
  - **Gate G3**: 100% test query coverage (20/20 canonical queries).
  - **Gate G4**: 100% Pydantic v2 schema validity.
  - **Gate G5**: **Zero URL Leaks** (recursively strips all `http://`, `https://`, `www.`, `.com`, markdown links/images, and HTML tags).
  - **Block A1**: All goals match regex `Follow these steps to perform this <Name> Troubleshooting.`; titles are exactly 2-3 words; descriptions are exactly 5-7 words starting with `"It will "`.
  - **Block A2**: All `auto` actions possess an actionable deeplink.
  - **Block A5**: 9 unique, diverse query variations per query in `results.jsonl`.

---

## 📂 Project Structure

```
.
├── theme2/                          # Core Theme 2 implementation
│   ├── src/
│   │   ├── api.py                   # FastAPI application & endpoints
│   │   ├── cache.py                 # Multi-tier caching engine (SQLite + in-memory)
│   │   ├── compiler.py              # Stage 2 SIIS procedure compiler
│   │   ├── deeplink_resolver.py     # BM25 + MiniLM embedding index for 578 deeplinks
│   │   ├── normalizer.py            # Stage 1 complaint normalizer
│   │   ├── pipeline.py              # Orchestrator connecting all components
│   │   ├── sanitizer.py             # Enforcer of regex, word counts & zero URL leaks
│   │   └── schema.py                # Official Pydantic v2 response & request schemas
│   ├── static/
│   │   └── index.html               # Interactive web demo console
│   ├── tests/
│   │   ├── test_contracts.py        # Automated contract and schema tests
│   │   ├── test_cache.py            # Latency and cache hit benchmarks
│   │   ├── test_api.py              # FastAPI endpoint tests
│   │   └── run_eval.py              # 20-query offline evaluation runner
│   ├── submission/
│   │   └── results.jsonl            # Official offline results file
│   ├── data/student_kit/            # Official dataset (deeplinks, siis_responses, schema)
│   ├── requirements.txt             # Project dependencies
│   ├── Dockerfile                   # Production container definition
│   └── README.md                    # Theme 2 technical documentation
├── CollegeName_TeamName_Submission.pptx # Hackathon presentation template
├── LangAI3.0_AI_Disclosure.docx     # AI disclosure declaration
├── SPEC.md                          # Implementation specification
├── PLAN.md                          # Project execution plan
└── EVAL.md                          # Evaluation and test protocol
```

---

## ⚡ Quickstart

### 1. Installation
```bash
pip install -r theme2/requirements.txt
```

### 2. Run the Server
```bash
python -m uvicorn theme2.src.api:app --host 0.0.0.0 --port 8000
```

### 3. Open the Interactive Console
Navigate to [http://localhost:8000/](http://localhost:8000/) in your browser.

### 4. Run Automated Tests
```bash
python -m pytest theme2/tests/test_contracts.py theme2/tests/test_cache.py theme2/tests/test_api.py -v
```

### 5. Generate / Verify Offline Submission
```bash
python -m theme2.tests.run_eval
```
Output is saved to `theme2/submission/results.jsonl`.
