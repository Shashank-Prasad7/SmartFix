"""Run the complete feasible local gate and retain exact command output."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
FRONTEND = ROOT / "frontend"


def source_fingerprint() -> str:
    relevant = [*sorted((ROOT / "src").glob("*.py")), *sorted((ROOT / "tests").glob("*.py")),
                *sorted((ROOT / "scripts").glob("*.py")),
                *sorted(path for path in (ROOT / "frontend" / "src").rglob("*") if path.is_file()),
                ROOT / "frontend" / "index.html", ROOT / "frontend" / "package.json",
                ROOT / "frontend" / "pnpm-lock.yaml", ROOT / "frontend" / "vite.config.mjs",
                ROOT / "Dockerfile", ROOT / "requirements.txt", ROOT / "requirements-dev.txt",
                ROOT / "data" / "official" / "manifest.json",
                ROOT / "data" / "fixtures" / "development_articles.json",
                ROOT / "data" / "fixtures" / "development_fact_pairs.json",
                ROOT / "data" / "fixtures" / "cache_adversaries.json"]
    hasher = hashlib.sha256()
    for path in relevant:
        hasher.update(str(path.relative_to(ROOT)).encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> int:
    run_id = f"release-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    report = ROOT / "reports" / run_id
    report.mkdir(parents=True, exist_ok=False)
    python = str(Path(sys.executable).resolve())
    commands = [
        ("provenance", REPO, [python, "-m", "theme2.scripts.verify_provenance"]),
        ("tests", REPO, [python, "-m", "pytest", "theme2/tests", "-q"]),
        ("lint", REPO, [str(ROOT / ".venv" / "Scripts" / "ruff.exe"), "check", "theme2/src", "theme2/tests", "theme2/scripts"]),
        ("typescript", FRONTEND, [str(FRONTEND / "node_modules" / ".bin" / "tsc.cmd"), "--noEmit"]),
        ("frontend_build", FRONTEND, [str(FRONTEND / "node_modules" / ".bin" / "vite.cmd"), "build", "--config", "vite.config.mjs", "--configLoader", "runner"]),
        ("review_pack", REPO, [python, "-m", "theme2.scripts.prepare_review", "--check"]),
        ("development", REPO, [python, "-m", "theme2.scripts.run_development"]),
        ("official_export", REPO, [python, "-m", "theme2.tests.run_eval"]),
        ("clean_copy", REPO, [python, "-m", "theme2.scripts.verify_clean_copy"]),
        ("fresh_dependencies", REPO, [python, "-m", "theme2.scripts.verify_fresh_dependencies"]),
        ("loopback", REPO, [python, "-m", "theme2.scripts.benchmark_local"]),
        ("cache_scale", REPO, [python, "-m", "theme2.scripts.benchmark_cache_scale"]),
        ("submission_artifacts", REPO, [python, "-m", "theme2.scripts.verify_submission_artifacts"]),
    ]
    outcomes: list[dict[str, object]] = []
    for name, cwd, command in commands:
        started = time.perf_counter()
        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=180, check=False)
            stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stdout, stderr, exit_code = "", type(exc).__name__, 1
        (report / f"{name}.stdout.txt").write_text(stdout, encoding="utf-8")
        (report / f"{name}.stderr.txt").write_text(stderr, encoding="utf-8")
        item = {"check": name, "status": "PASS" if exit_code == 0 else "FAIL", "exit_code": exit_code,
                "command": command, "cwd": str(cwd), "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "stdout_file": f"{name}.stdout.txt", "stderr_file": f"{name}.stderr.txt"}
        outcomes.append(item)
        print(f"{name}: {item['status']} exit={exit_code} elapsed={item['elapsed_ms']}ms")
    export = ROOT / "submission" / "results.jsonl"
    summary = {"run_id": run_id, "source_fingerprint_sha256": source_fingerprint(),
               "checks": outcomes, "passed": sum(item["status"] == "PASS" for item in outcomes),
               "failed": sum(item["status"] == "FAIL" for item in outcomes),
               "submission_export_lines": len(export.read_text(encoding="utf-8").splitlines()) if export.is_file() else 0,
               "measurement_boundary": "loopback is local deterministic timing; no hosted, independent semantic, Docker, or public endpoint gate"}
    (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"RELEASE LOCAL SUMMARY: {summary['passed']}/{len(outcomes)} PASS, export lines={summary['submission_export_lines']}; report={report}")
    return 0 if summary["failed"] == 0 and summary["submission_export_lines"] == 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
