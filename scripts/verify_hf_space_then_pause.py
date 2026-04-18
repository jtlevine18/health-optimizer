"""One-shot verification: wait for HF Space build, trigger pipeline run,
gather diagnostics, then pause the Space.

Ephemeral script — meant to be run once end-to-end after a push to the
jtlevine/market-intelligence HF Space. Writes a summary to stdout;
intended to run in the background so Claude Code gets one notification
when the whole flow completes.
"""
from __future__ import annotations

import json
import sys
import time

import requests
from huggingface_hub import get_space_runtime, pause_space

SPACE = "jtlevine/market-intelligence"
BASE = "https://jtlevine-market-intelligence.hf.space"

BUILD_DEADLINE_SEC = 900      # 15 min to build
PIPELINE_DEADLINE_SEC = 900   # 15 min for the pipeline run (first cold-start can be 5-8 min)
BUILD_POLL_SEC = 30
PIPELINE_POLL_SEC = 30


def banner(msg: str) -> None:
    print(f"\n========== {msg} ==========", flush=True)


def wait_for_build() -> str:
    """Block until the Space is RUNNING (or errored). Returns the final stage."""
    banner("WAIT FOR BUILD")
    deadline = time.time() + BUILD_DEADLINE_SEC
    last_stage = None
    while time.time() < deadline:
        r = get_space_runtime(SPACE)
        stage = r.stage
        if stage != last_stage:
            print(f"[build] stage={stage} hw={r.hardware} requested_hw={r.requested_hardware}", flush=True)
            last_stage = stage
        if stage == "RUNNING":
            return stage
        if stage in ("BUILD_ERROR", "RUNTIME_ERROR", "STOPPED", "DELETED", "NO_APP_FILE", "CONFIG_ERROR"):
            print(f"[build] FAILED runtime: {json.dumps(r.raw, indent=2)}", flush=True)
            return stage
        time.sleep(BUILD_POLL_SEC)
    return "TIMEOUT"


def trigger_pipeline() -> dict:
    banner("TRIGGER PIPELINE")
    try:
        resp = requests.post(f"{BASE}/api/pipeline/trigger", timeout=60)
        print(f"[trigger] status={resp.status_code} body={resp.text[:500]}", flush=True)
        return {"ok": resp.ok, "status_code": resp.status_code, "body": resp.text[:500]}
    except Exception as exc:
        print(f"[trigger] ERROR {type(exc).__name__}: {exc}", flush=True)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def wait_for_pipeline() -> dict:
    banner("WAIT FOR PIPELINE")
    deadline = time.time() + PIPELINE_DEADLINE_SEC
    last_step = None
    last_status = None
    while time.time() < deadline:
        try:
            resp = requests.get(f"{BASE}/api/pipeline/status", timeout=30)
            status = resp.json()
        except Exception as exc:
            print(f"[status] ERROR {type(exc).__name__}: {exc}", flush=True)
            time.sleep(PIPELINE_POLL_SEC)
            continue

        running = status.get("running", False)
        step = status.get("current_step", status.get("step", "?"))
        if step != last_step or running != last_status:
            print(f"[status] running={running} step={step}", flush=True)
            last_step = step
            last_status = running

        if not running and status.get("last_run") is not None:
            return status
        if not running and step in ("complete", "done", None, "?"):
            return status
        time.sleep(PIPELINE_POLL_SEC)
    return {"timeout": True}


def fetch_diagnostics() -> dict:
    banner("DIAGNOSTICS")
    out: dict = {}
    for path in ["/health", "/api/health", "/api/pipeline/status"]:
        try:
            resp = requests.get(f"{BASE}{path}", timeout=30)
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:500]
            out[path] = {"status_code": resp.status_code, "body": body}
            print(f"[{path}] {resp.status_code}: {json.dumps(body, default=str)[:400]}", flush=True)
        except Exception as exc:
            out[path] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"[{path}] ERROR {type(exc).__name__}: {exc}", flush=True)
    return out


def pause() -> None:
    banner("PAUSE SPACE")
    try:
        r = pause_space(SPACE)
        print(f"[pause] ok stage={getattr(r, 'stage', '?')}", flush=True)
    except Exception as exc:
        print(f"[pause] ERROR {type(exc).__name__}: {exc}", flush=True)


def main() -> int:
    stage = wait_for_build()
    if stage != "RUNNING":
        banner(f"BUILD NOT RUNNING: stage={stage}")
        print("[overall] Skipping pipeline test; pausing anyway.", flush=True)
        pause()
        return 2

    # Give the uvicorn app a moment after the container reports READY.
    time.sleep(30)

    trigger = trigger_pipeline()
    # Even if trigger fails, still try to gather diagnostics before pausing.
    if trigger.get("ok"):
        final_status = wait_for_pipeline()
    else:
        final_status = {"skipped_pipeline_wait": True, "reason": trigger.get("error") or trigger.get("body")}

    diag = fetch_diagnostics()

    banner("SUMMARY")
    summary = {
        "space": SPACE,
        "build_stage": stage,
        "trigger": trigger,
        "final_status": final_status,
        "diag": diag,
    }
    print(json.dumps(summary, indent=2, default=str), flush=True)

    pause()
    return 0 if trigger.get("ok") and not final_status.get("timeout") else 1


if __name__ == "__main__":
    sys.exit(main())
