"""Bounded free-tier generation smoke test; never records keys or model text."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

from theme2.scripts.probe_provider_access import ROOT, load_keys


def _request(url: str, headers: dict[str, str], body: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.load(response)


def _probe(name: str, model: str, url: str, headers: dict[str, str], body: dict[str, object]) -> dict[str, object]:
    started = time.perf_counter()
    try:
        status, data = _request(url, headers, body)
        if name == "gemini":
            candidates = data.get("candidates") or []
            content = candidates[0].get("content", {}) if candidates else {}
            has_text = any(bool(part.get("text")) for part in content.get("parts", []))
            usage = data.get("usageMetadata") or {}
            counts = {key: value for key, value in usage.items()
                      if key in {"promptTokenCount", "candidatesTokenCount", "totalTokenCount", "thoughtsTokenCount"}
                      and isinstance(value, int)}
            resolved = data.get("modelVersion")
        else:
            choices = data.get("choices") or []
            has_text = bool(choices and (choices[0].get("message") or {}).get("content"))
            usage = data.get("usage") or {}
            counts = {key: value for key, value in usage.items()
                      if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                      and isinstance(value, int)}
            resolved = data.get("model")
        return {"status": "PASS" if status == 200 and has_text else "FAIL", "http_status": status,
                "model": model, "resolved_model": resolved if isinstance(resolved, str) else None,
                "nonempty_text": has_text, "usage_tokens": counts,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "generation_calls": 1}
    except urllib.error.HTTPError as exc:
        safe_codes = {"invalid_api_key", "permission_denied", "model_not_allowed",
                      "blocked_api_access", "rate_limit_exceeded", "insufficient_quota",
                      "resource_exhausted", "unavailable"}
        try:
            error = json.load(exc).get("error") or {}
            code = str(error.get("code") or error.get("type") or error.get("status") or "").lower()
        except (ValueError, TypeError, AttributeError):
            code = ""
        return {"status": "FAIL", "http_status": exc.code, "model": model,
                "error_class": "HTTPError", "safe_error_code": code if code in safe_codes else "unclassified",
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "generation_calls": 1}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError) as exc:
        return {"status": "FAIL", "http_status": None, "model": model,
                "error_class": type(exc).__name__, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "generation_calls": 1}


def main() -> int:
    keys = load_keys()
    results: dict[str, object] = {}
    for model in ("gemini-3.1-flash-lite", "gemini-3.8-flash"):
        results[model] = _probe(
            "gemini", model,
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            {"x-goog-api-key": keys["GEMINI_API_KEY"]},
            {"contents": [{"parts": [{"text": "Reply with exactly OK."}]}],
             "generationConfig": {"temperature": 0, "maxOutputTokens": 16}},
        )
    results["groq"] = _probe(
        "groq", "llama-3.1-8b-instant", "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {keys['GROQ_API_KEY']}"},
        {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "Reply with exactly OK."}],
         "temperature": 0, "max_tokens": 16},
    )
    run_id = "hosted-smoke-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    report = {"run_id": run_id, "checked_at_utc": datetime.now(UTC).isoformat(),
              "account_tier_basis": "user-confirmed free tier; not independently visible to script",
              "scope": "Tiny generation probes only; no customer or article text; no response text or raw errors retained",
              "actual_charges": "unknown; check provider dashboards", "results": results}
    path = ROOT / "reports" / f"{run_id}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for model, result in results.items():
        print(f"{model}: {result['status']} http={result['http_status']} elapsed_ms={result['elapsed_ms']}")
    print(f"REPORT: {path}")
    return 0 if all(result["status"] == "PASS" for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
