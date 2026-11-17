"""Reproduce installation in a disposable source copy, never resetting working data."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
steps = []
logs = []
with tempfile.TemporaryDirectory(prefix="battery-clean-install-") as directory:
    target = Path(directory)
    for name in ["apps", "scripts", "tests"]:
        shutil.copytree(
            ROOT / name,
            target / name,
            ignore=shutil.ignore_patterns("__pycache__", "battery-vision", ".DS_Store"),
        )
    shutil.copytree(ROOT / "data/seed", target / "data/seed")
    (target / "docs").mkdir()
    for name in [
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "vite.config.ts",
        "pyproject.toml",
    ]:
        shutil.copy2(ROOT / name, target / name)
    commands = [
        ("Create clean Python environment", [sys.executable, "-m", "venv", ".venv"]),
        (
            "Install locked Python and dev dependencies",
            [".venv/bin/pip", "install", "-r", "apps/api/requirements-dev.txt"],
        ),
        ("Install locked Node dependencies", ["npm", "ci", "--no-audit", "--no-fund"]),
        ("Python lint", [".venv/bin/ruff", "check", "apps/api", "scripts"]),
        (
            "Isolated backend workflow tests",
            [".venv/bin/python", "-m", "pytest", "apps/api/tests", "-q"],
        ),
        ("TypeScript and frontend production build", ["npm", "run", "build"]),
    ]
    env = dict(os.environ)
    for key in ["DATABASE_URL", "TEST_DATABASE_URL", "TESSERACT_BIN", "PYTHONPATH"]:
        env.pop(key, None)
    env.update(DEMO_MODE="true", DATA_MODE="fixture", ASSESSMENT_DATE="2026-11-16")
    for label, command in commands:
        print(label, flush=True)
        start = time.monotonic()
        result = subprocess.run(
            command,
            cwd=target,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        logs.append(label + "\n" + result.stdout)
        steps.append(
            {
                "step": label,
                "exit_code": result.returncode,
                "seconds": round(time.monotonic() - start, 2),
            }
        )
        if result.returncode:
            break
summary = {
    "environment": "Fresh dependency install in a disposable copy on the same macOS machine; not a second-machine test",
    "python": sys.version.split()[0],
    "steps": steps,
    "passed": len(steps) == len(commands) and all(s["exit_code"] == 0 for s in steps),
}
(ROOT / "docs/clean-install.json").write_text(json.dumps(summary, indent=2))
(ROOT / "docs/clean-install.log").write_text("\n\n".join(logs))
print(json.dumps(summary), flush=True)
raise SystemExit(0 if summary["passed"] else 1)
