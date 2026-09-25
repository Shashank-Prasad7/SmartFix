"""Reproduce Python tests and official export from an isolated source copy.

This uses the existing project virtual environment. It checks package/source
independence, not fresh dependency installation, Docker, or public hosting.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
RUNTIME = ROOT / ".runtime"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
FILES = ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "Dockerfile", "README.md", "AGENTS.md", "SPEC.md", "PLAN.md", "EVAL.md"]
DIRS = ["src", "tests", "scripts", "data/official/student_kit", "data/fixtures", "static"]


def main() -> int:
    if not PYTHON.is_file():
        raise FileNotFoundError("Project virtual environment is required for this check")
    RUNTIME.mkdir(exist_ok=True)
    run_id = f"clean-copy-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
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
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("app", "__pycache__", "*.pyc"))
        (project / ".runtime").mkdir()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(scratch)
        env["PRISM_CACHE_DB_PATH"] = str(project / ".runtime" / "clean.sqlite3")
        commands = [
            ("tests", [str(PYTHON), "-m", "pytest", "theme2/tests", "-q"]),
            ("export", [str(PYTHON), "-m", "theme2.tests.run_eval"]),
        ]
        outcomes: list[dict[str, object]] = []
        for name, command in commands:
            result = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=120, check=False)
            (report / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
            (report / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
            outcomes.append({"check": name, "command": " ".join(command), "exit_code": result.returncode,
                             "working_directory": "isolated source copy", "stdout_file": f"{name}.stdout.txt", "stderr_file": f"{name}.stderr.txt"})
            print(f"CLEAN COPY {name}: exit={result.returncode}")
            if result.returncode:
                print(result.stdout[-2000:])
                print(result.stderr[-2000:])
                break
        export = project / "submission" / "results.jsonl"
        line_count = len(export.read_text(encoding="utf-8").splitlines()) if export.is_file() else 0
        summary = {"run_id": run_id, "scope": "source copy with existing project virtual environment; no fresh install or Docker",
                   "tests_and_export": outcomes, "export_lines": line_count,
                   "passed": len(outcomes) == 2 and all(item["exit_code"] == 0 for item in outcomes) and line_count == 20}
        (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"CLEAN COPY SUMMARY: {'PASS' if summary['passed'] else 'FAIL'}, export lines={line_count}, report={report}")
        return 0 if summary["passed"] else 1
    finally:
        resolved = scratch.resolve()
        if not resolved.is_relative_to(RUNTIME.resolve()):
            raise ValueError("Refusing recursive cleanup outside project runtime")
        shutil.rmtree(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
