#!/usr/bin/env python3
"""
Vibe Prompts E2E: 15-second commercial via API.
Drives the full pipeline through the backend API without any frontend.

Usage:
    python tests/api_15s_commercial.py [--base-url http://localhost:8000]
"""

import argparse
import json
import logging
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api-15s")

DEFAULT_BASE = "http://localhost:8000"
MAX_PIPELINE_MINUTES = 45
POLL_INTERVAL_S = 10


def api_get(base: str, path: str, timeout: int = 30) -> dict:
    url = f"{base}{path}"
    req = Request(url)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def api_post(base: str, path: str, body: dict, timeout: int = 120) -> dict:
    url = f"{base}{path}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def consume_sse_stream(base: str, session_id: str, message: str, timeout: int = 600) -> str:
    """Send a message via SSE stream and consume the full response."""
    params = urlencode({"user_id": "default-user", "message": message})
    url = f"{base}/api/v1/run/{session_id}/stream?{params}"
    req = Request(url)

    last_text = ""
    try:
        with urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                        parts = event.get("data", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                last_text = part["text"]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        log.warning(f"Stream ended: {e}")

    return last_text


def poll_for_key(base: str, session_id: str, key: str, timeout_s: int = 600) -> any:
    """Poll session state until a key is populated."""
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            result = api_get(base, f"/api/v1/sessions/{session_id}/state?user_id=default-user")
            state = result.get("state", result)
            value = state.get(key)
            if value is not None and value != "" and value != [] and value != {}:
                elapsed = int(time.time() - start)
                log.info(f'Key "{key}" populated after {elapsed}s')
                return value
        except Exception as e:
            log.debug(f"Poll error: {e}")
        time.sleep(POLL_INTERVAL_S)

    raise TimeoutError(f'Timed out waiting for key "{key}" after {timeout_s}s')


def run_15s_pipeline(base: str):
    pipeline_start = time.time()

    # ── PHASE 1: Create session with Pixel config + pre-selected trends ──
    log.info("PHASE 1: Creating session with Google Pixel config, 15s commercial, pre-selected trends")
    session = api_post(base, "/api/v1/sessions", {
        "initial_state": {
            "brand": "Google Pixel",
            "target_product": "Pixel 9 Pro",
            "target_audience": "Tech-savvy millennials and Gen Z creators who value AI-powered photography",
            "key_selling_points": "AI-powered camera with Best Take, Magic Eraser, Tensor G4 chip, 7 years of updates, Gemini AI built-in",
            "commercial_duration": 15,
            "autopilot_mode": True,
            # Pre-select trends so root_agent skips trend-discovery
            "target_search_trends": {
                "target_search_trends": [
                    {
                        "trend_title": "AI photography",
                        "trend_rank": 1,
                        "trend_refresh_date": "03/01/2026",
                    }
                ]
            },
            "target_yt_trends": {
                "target_yt_trends": [
                    {
                        "video_title": "Pixel 9 Pro Camera Review - AI Features Deep Dive",
                        "video_duration": "PT12M30S",
                        "video_url": "https://www.youtube.com/watch?v=example123",
                    }
                ]
            },
        },
    })
    session_id = session["session_id"]
    log.info(f"Session created: {session_id}")

    # ── PHASE 2: Start pipeline ──────────────────────────────────────────
    # Use the same message pattern as the frontend's handleStart() which is
    # proven to work in existing E2E tests.
    log.info("PHASE 2: Starting pipeline (skipping trend discovery)")
    start_msg = (
        "Start the full pipeline, producing a 15-second commercial. "
        "Campaign metadata and trends are already configured in session state "
        "— skip trend-discovery and proceed directly to market research. "
        "Use auto-select mode for trends, approve all outputs automatically, "
        "and proceed through all steps without pausing for user confirmation."
    )
    response = consume_sse_stream(base, session_id, start_msg, timeout=600)
    log.info(f"Initial response: {response[:200]}...")

    # ── PHASE 3: Auto-approve loop ───────────────────────────────────────
    # The pipeline will pause at various points for approval.
    # We send approval messages repeatedly until the commercial is generated.
    approval_count = 0
    max_approvals = 20

    while approval_count < max_approvals:
        elapsed_min = (time.time() - pipeline_start) / 60
        if elapsed_min > MAX_PIPELINE_MINUTES:
            raise TimeoutError(f"Pipeline exceeded {MAX_PIPELINE_MINUTES} min")

        # Check if commercial is already done
        try:
            result = api_get(base, f"/api/v1/sessions/{session_id}/state?user_id=default-user")
            state = result.get("state", result)
            if state.get("commercial_artifact"):
                log.info("Commercial artifact found! Pipeline complete.")
                break
        except Exception:
            pass

        # Send approval
        approval_count += 1
        log.info(f"APPROVAL {approval_count}: Sending approval at {elapsed_min:.1f} min")
        try:
            response = consume_sse_stream(
                base, session_id,
                "Looks good, proceed with all options.",
                timeout=600,
            )
            log.info(f"Approval {approval_count} response: {response[:200]}...")
        except Exception as e:
            log.warning(f"Approval {approval_count} error: {e}")

        # Wait a bit before next check
        time.sleep(15)

    # ── PHASE 4: Final verification ──────────────────────────────────────
    log.info("PHASE 4: Final verification")

    result = api_get(base, f"/api/v1/sessions/{session_id}/state?user_id=default-user")
    state = result.get("state", result)

    # Verify key outputs
    assert state.get("brand"), "Missing brand"
    assert state.get("target_product"), "Missing target_product"
    assert state.get("commercial_duration") == 15, f"Duration is {state.get('commercial_duration')}, expected 15"
    if not state.get("combined_final_cited_report"):
        log.warning("Research report not generated (pipeline may have skipped research in autopilot mode)")
    else:
        log.info(f"Research report: {len(state['combined_final_cited_report'])} chars")

    # Image artifacts
    img_keys = state.get("img_artifact_keys", {})
    if isinstance(img_keys, dict):
        img_list = img_keys.get("img_artifact_keys", [])
    else:
        img_list = img_keys if isinstance(img_keys, list) else []
    assert len(img_list) >= 2, f"Expected >= 2 images, got {len(img_list)}"

    # Video artifacts
    vid_keys = state.get("vid_artifact_keys", {})
    if isinstance(vid_keys, dict):
        vid_list = vid_keys.get("vid_artifact_keys", [])
    else:
        vid_list = vid_keys if isinstance(vid_keys, list) else []
    assert len(vid_list) >= 2, f"Expected >= 2 videos, got {len(vid_list)}"

    # Commercial
    commercial = state.get("commercial_artifact")
    assert commercial, "Missing commercial_artifact"
    artifact_key = commercial if isinstance(commercial, str) else commercial.get("artifact_key", "")
    assert "commercial" in artifact_key.lower(), f"Commercial key doesn't match: {artifact_key}"

    total_min = (time.time() - pipeline_start) / 60

    print()
    print("=" * 50)
    print("  [API 15s] E2E Pipeline Complete")
    print(f"  Session:    {session_id}")
    print(f"  Commercial: {artifact_key}")
    print(f"  Images:     {len(img_list)}")
    print(f"  Videos:     {len(vid_list)}")
    print(f"  Duration:   {total_min:.1f} min")
    print(f"  Approvals:  {approval_count}")
    print("=" * 50)
    print()

    return {
        "session_id": session_id,
        "commercial": artifact_key,
        "images": len(img_list),
        "videos": len(vid_list),
        "duration_min": total_min,
    }


def main():
    parser = argparse.ArgumentParser(description="API 15s commercial E2E test")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="API base URL")
    args = parser.parse_args()

    try:
        result = run_15s_pipeline(args.base_url)
        log.info(f"SUCCESS: 15s commercial generated in {result['duration_min']:.1f} min")
        sys.exit(0)
    except Exception as e:
        log.error(f"FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
