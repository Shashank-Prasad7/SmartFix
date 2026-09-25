"""Reinstall dependencies offline in an isolated project copy and rerun gates.

Uses only the local uv and pnpm stores. This is a clean dependency environment
check, not a Docker build or public deployment.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
FILES = ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "Dockerfile"]
DIRS = ["src", "tests", "scripts", "data/official/student_kit", "data/fixtures", "frontend", "static"]


def main() -> int:
    uv = shutil.which("uv")
    pnpm = shutil.which("pnpm")
    if not uv or not pnpm:
        raise RuntimeError("Local uv and pnpm executables are required")
    RUNTIME.mkdir(exist_ok=True)
    run_id = f"fresh-deps-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    report = ROOT / "reports" / run_id
    report.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix=f"{run_id}-", dir=RUNTIME)).resolve()
    if not scratch.is_relative_to(RUNTIME.resolve()):
        raise ValueError("Scratch directory escaped project runtime")
    try:
        project = scratch / "theme2"
        project.mkdir()
        for relative in FILES:
            shutil.copy2(ROOT / relative, project / relative)
        for relative in DIRS:
            source = ROOT / relative
            destination = project / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("node_modules", "app", "__pycache__", "*.pyc"))
        (project / ".runtime").mkdir()
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(RUNTIME / "uv-cache")
        env["PYTHONPATH"] = str(scratch)
        env["PRISM_CACHE_DB_PATH"] = str(project / ".runtime" / "fresh.sqlite3")
        venv = scratch / "venv"
        python = venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"
        commands = [
            ("venv", scratch, [uv, "venv", str(venv), "--python", sys.executable, "--offline"]),
            ("python_install", scratch, [uv, "pip", "install", "--offline", "--python", str(python), "-r", str(project / "requirements-dev.txt")]),
            ("frontend_install", project / "frontend", [pnpm, "install", "--offline", "--frozen-lockfile", "--store-dir", str(RUNTIME / "pnpm-store")]),
            ("typescript", project / "frontend", [str(project / "frontend" / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")), "--noEmit"]),
            ("frontend_build", project / "frontend", [str(project / "frontend" / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")), "build", "--config", "vite.config.mjs", "--configLoader", "runner"]),
            ("tests", scratch, [str(python), "-m", "pytest", "theme2/tests", "-q"]),
            ("export", scratch, [str(python), "-m", "theme2.tests.run_eval"]),
        ]
        outcomes = []
        for name, cwd, command in commands:
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180, check=False)
            (report / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
            (report / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
            outcomes.append({"name": name, "command": command, "exit_code": result.returncode})
            print(f"FRESH DEPS {name}: exit={result.returncode}")
            if result.returncode:
                print(result.stderr[-1000:])
                break
        export = project / "submission" / "results.jsonl"
        lines = len(export.read_text(encoding="utf-8").splitlines()) if export.is_file() else 0
        passed = len(outcomes) == len(commands) and all(item["exit_code"] == 0 for item in outcomes) and lines == 20
        summary = {"run_id": run_id, "scope": "isolated project copy, new offline Python venv and pnpm install from local stores",
                   "commands": outcomes, "export_lines": lines, "passed": passed,
                   "limits": "Existing local dependency caches; no Docker or public host"}
        (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"FRESH DEPS SUMMARY: {'PASS' if passed else 'FAIL'}, export lines={lines}; report={report}")
        return 0 if passed else 1
    finally:
        if not scratch.resolve().is_relative_to(RUNTIME.resolve()):
            raise ValueError("Refusing recursive cleanup outside project runtime")
        shutil.rmtree(scratch)


if __name__ == "__main__":
    raise SystemExit(main())
