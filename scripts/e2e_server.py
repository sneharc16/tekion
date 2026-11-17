"""Run browser checks against a disposable database, never the working demo."""

import os
import subprocess
import tempfile
import time
import signal
import sys
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="battery-e2e-") as directory:
    env = dict(
        os.environ,
        DATABASE_URL="sqlite:///" + str(Path(directory) / "e2e.db"),
        DEMO_MODE="true",
        DATA_MODE="fixture",
        ASSESSMENT_DATE="2026-11-16",
        PUBLIC_BASE_URL="http://127.0.0.1:5175",
        VITE_API_TARGET="http://127.0.0.1:8001",
    )
    processes = []

    def stop(*args):
        for p in reversed(processes):
            if p.poll() is None:
                p.terminate()
        for p in reversed(processes):
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "apps.api.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8001",
                ],
                env=env,
            )
        )
        processes.append(
            subprocess.Popen(
                ["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5175"],
                env=env,
            )
        )
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
    finally:
        stop()
