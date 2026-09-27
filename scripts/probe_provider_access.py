"""Read-only provider model-list probe with no credential or account logging."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_FILE = ROOT / ".runtime" / "provider.env"
GEMINI_MODELS = ("gemini-3.1-flash-lite", "gemini-3.8-flash")
GROQ_MODELS = ("llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-120b")


def load_keys() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in SECRET_FILE.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name in {"GEMINI_API_KEY", "GROQ_API_KEY"}:
            if name in values:
                raise ValueError("Duplicate provider key name")
            values[name] = value.strip().strip('"').strip("'")
    if not all(values.get(name) for name in ("GEMINI_API_KEY", "GROQ_API_KEY")):
        raise ValueError("Both provider keys must be present")
    return values


def list_models(url: str, header: str, key: str, field: str, candidates: tuple[str, ...]) -> dict[str, object]:
    request = urllib.request.Request(url, headers={header: key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.load(response)
        models = data[field]
        ids = {str(item["name" if field == "models" else "id"]).removeprefix("models/") for item in models}
        return {
            "status": "PASS", "http_status": 200, "models_returned": len(ids),
            "candidate_available": {name: name in ids for name in candidates},
            "billing_tier": "unknown", "generation_calls": 0,
        }
    except urllib.error.HTTPError as exc:
        return {"status": "FAIL", "http_status": exc.code, "error_type": "HTTPError", "generation_calls": 0}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "FAIL", "http_status": None, "error_type": type(exc).__name__, "generation_calls": 0}


def main() -> int:
    keys = load_keys()
    gemini = list_models(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
        "x-goog-api-key", keys["GEMINI_API_KEY"], "models", GEMINI_MODELS,
    )
    groq = list_models(
        "https://api.groq.com/openai/v1/models",
        "Authorization", f"Bearer {keys['GROQ_API_KEY']}", "data", GROQ_MODELS,
    )
    run_id = "provider-access-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    report = {
        "run_id": run_id,
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Read-only GET model lists; no generation, account or quota claims",
        "gemini": gemini,
        "groq": groq,
    }
    path = ROOT / "reports" / f"{run_id}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, result in (("gemini", gemini), ("groq", groq)):
        print(f"{name}: {result['status']} http={result['http_status']} candidates={result.get('candidate_available', {})}")
    print(f"REPORT: {path}")
    return 0 if gemini["status"] == groq["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
