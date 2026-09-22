# Samsung PRISM GenAI Hackathon 3.0 (Theme 2)
## Smart Guided Troubleshooting Engine

### 1. Project Overview
This repository contains the production implementation of the **Smart Guided Troubleshooting Engine** for Theme 2. The system transforms natural-language device complaints and raw SIIS (Samsung Internal Knowledge Store) articles into structured, verified troubleshooting guides enriched with Galaxy Settings deeplinks.

### 2. Key Architecture & Highlights
- **FastAPI REST Service**: Exposes `GET /health` (`{"status": "ok"}`) and `POST /v1/troubleshoot` conforming strictly to the official `ContextDeeplinkResponse` schema.
- **Two-Stage Processing Pipeline**:
  - **Stage 1 (Complaint Normalization)**: Standardizes user intent, technical complaint, feature area, and extracted device facts.
  - **Stage 2 (SIIS Procedure Compiler)**: Chunks and compiles SIIS knowledge articles into verified actions and steps without inventing ungrounded advice.
- **Dual-Index Deeplink Resolver**: Hybrid lexical BM25 + dense sentence-transformers (`all-MiniLM-L6-v2`) indexing over all 578 Galaxy Settings deeplinks in `deeplinks.json`, with operation disambiguation (enable vs disable, Bluetooth vs Bluetooth scanning, Factory Reset vs Auto Reset) and validation deeplink copying.
- **Multi-Tier Latency & Caching ($\le 300\text{ ms}$ p95)**:
  - **Tier 1 (Exact Answer Cache)**: Sub-millisecond ($<0.1\text{ ms}$) in-memory hash lookup.
  - **Tier 2 (Semantic Paraphrase Cache)**: $<30\text{ ms}$ lookup via cosine similarity over query embeddings ($\ge 80\%$ hit rate target).
  - **Tier 3 (Compiled Procedure Cache)**: Instantaneous reuse of compiled procedures across varying queries for the same article.
- **Strict Scoring Gate Guarantees**:
  - **Gate G2**: `GET /health` returns `{"status": "ok"}`.
  - **Gate G3**: 100% test query coverage (20/20 canonical queries).
  - **Gate G4**: 100% Pydantic v2 schema validity.
  - **Gate G5**: Zero URL leaks (recursively strips all `http://`, `https://`, `www.`, `.com`, markdown links/images, and HTML tags).
  - **Block A1**: All goals match regex `Follow these steps to perform this <Name> Troubleshooting.`; titles are exactly 2-3 words; descriptions are exactly 5-7 words starting with `"It will "`.
  - **Block A2**: All `auto` actions possess an actionable deeplink.
  - **Block A5**: 9 unique, diverse query variations per query in `results.jsonl`.

---

### 3. Quickstart & Setup

#### Prerequisites
- Python 3.10+
- Recommended: Google Gemini API key (set in environment or `.env` file)

#### Installation
```bash
# Clone or navigate to the repository root
cd "Samsung Prism Hackathon"

# Install dependencies
pip install -r theme2/requirements.txt
```

#### Running the Server
```bash
# Start the FastAPI server on port 8000
python -m uvicorn theme2.src.api:app --host 0.0.0.0 --port 8000
```
Check health:
```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

---

### 4. Running Tests & Evaluations

#### Run Unit & Contract Tests
```bash
python -m pytest theme2/tests/test_contracts.py theme2/tests/test_cache.py theme2/tests/test_api.py -v
```

#### Generate Offline Submission (`results.jsonl`)
```bash
python -m theme2.tests.run_eval
```
This processes all 20 canonical queries from `siis_responses.json`, produces 9 variations per query, checks all scoring gates, and writes the output to `theme2/submission/results.jsonl`.

---

### 5. Final Submission Checklist
- [x] Working prototype code in GitHub repository.
- [x] Reproducible setup instructions in README.
- [x] Offline evaluation file generated: `theme2/submission/results.jsonl` (100% coverage, 0 URL leaks, 100% schema valid).
- [x] Required Git release tag:
  ```bash
  git tag -a PRISM_GENAI_HACKATHON_Y2026 -m "PRISM Gen AI Hackathon Y2026 Final Submission"
  git push origin PRISM_GENAI_HACKATHON_Y2026
  ```
- [x] Presentation deck ([CollegeName_TeamName_Submission.pptx](file:///c:/Users/shash/OneDrive/Documents/college/Projects/Samsung%20Prism%20Hackathon/CollegeName_TeamName_Submission.pptx)) and AI Disclosure form ([LangAI3.0_AI_Disclosure.docx](file:///c:/Users/shash/OneDrive/Documents/college/Projects/Samsung%20Prism%20Hackathon/LangAI3.0_AI_Disclosure.docx)).
