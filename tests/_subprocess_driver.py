"""Shared subprocess driver for tests/test_eval_*.py.

Phase 1.6 introduced three test files that spawn a fresh Python
subprocess per region — necessary because `src.pipeline` (and its
transitive imports) capture `from config import REGION, MANDIS, ...`
at module load time, so reloading config doesn't retroactively
update importers.

All three files shared the same env + sentinel + JSON-parse machinery;
this module factors it out so each test contributes only its driver
body (the code that actually runs inside the subprocess).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SENTINEL_BEGIN = "__PIPELINE_RESULT_BEGIN__"
_SENTINEL_END = "__PIPELINE_RESULT_END__"
_REPO_ROOT_PLACEHOLDER = "__REPO_ROOT__"


def run_driver(region: str, driver_body: str, timeout: int = 600) -> dict:
    """Run `driver_body` as the sole `-c` argument in a fresh Python process.

    The driver is expected to print one JSON object between the
    `__PIPELINE_RESULT_BEGIN__` / `__PIPELINE_RESULT_END__` sentinels.
    The placeholder `__REPO_ROOT__` in the driver body is replaced with
    `repr(REPO_ROOT)` so the subprocess can `sys.path.insert(0, ...)`
    before importing `src.*`.
    """
    env = os.environ.copy()
    env["MARKET_INTEL_REGION"] = region
    env["MARKET_INTEL_DEMO_MODE"] = "1"
    env.pop("ANTHROPIC_API_KEY", None)

    driver = driver_body.replace(_REPO_ROOT_PLACEHOLDER, repr(_REPO_ROOT))

    proc = subprocess.run(
        [sys.executable, "-c", driver],
        env=env,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Subprocess failed for region={region}:\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    stdout = proc.stdout
    start = stdout.find(_SENTINEL_BEGIN)
    end = stdout.find(_SENTINEL_END)
    if start < 0 or end < 0:
        raise AssertionError(
            f"Missing result sentinels in subprocess output:\n{stdout}"
        )
    payload = stdout[start + len(_SENTINEL_BEGIN) : end].strip()
    return json.loads(payload)


__all__ = ["run_driver"]
