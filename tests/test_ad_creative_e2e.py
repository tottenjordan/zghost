"""
Focused E2E test for ad content generator with reference image workflow.
Tests: generate top 2 ideas -> draft report -> image keyframe -> video with reference image.
"""
import os
import sys
import json
import time
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from dotenv import load_dotenv
load_dotenv("trends_and_insights_agent/.env")

from google.genai import types
from google.adk.runners import InMemoryRunner

# Pre-populated state to skip trend selection and research
MOCK_STATE = {
    "brand": "Pixel",
    "target_product": "Pixel 9 Pro",
    "target_audience": "Tech-savvy millennials and Gen Z who value photography, AI features, and premium design",
    "key_selling_points": "Best-in-class camera with AI-powered editing, Gemini AI assistant built-in, 7 years of OS updates, Tensor G4 chip",
    "target_search_trends": {"target_search_trends": [
        {"title": "AI Photography", "description": "Growing interest in AI-enhanced mobile photography and computational imaging"}
    ]},
    "target_yt_trends": {"target_yt_trends": [
        {"title": "Pixel 9 Camera Review", "description": "YouTubers comparing Pixel 9 Pro camera to iPhone and Samsung Galaxy"}
    ]},
    "yt_video_analysis": "YouTube trend analysis: Tech reviewers highlight Pixel 9 Pro's superior night photography, Magic Eraser, and Best Take features. Audiences respond strongly to side-by-side photo comparisons showing AI enhancement capabilities.",
    "combined_final_cited_report": """# Market Research Report: Pixel 9 Pro Campaign

## Executive Summary
The Pixel 9 Pro enters a competitive smartphone market where AI-powered features are the key differentiator. Consumer interest in AI photography has surged 340% YoY, with mobile photography being the #1 purchase driver for premium smartphones.

## Key Findings
1. **AI Photography Trend**: 78% of smartphone buyers cite camera quality as their top priority. AI-enhanced features like Magic Eraser and Best Take resonate strongly with the target demographic.
2. **YouTube Influence**: Tech review videos comparing camera capabilities drive 45% of premium smartphone purchase decisions among 18-34 year olds.
3. **Competitive Advantage**: Pixel 9 Pro's Tensor G4 chip enables on-device AI processing that competitors cannot match, resulting in faster photo editing and more natural results.

## Recommendations
- Lead with AI photography capabilities in ad creative
- Leverage side-by-side comparison format popular on YouTube
- Emphasize the "effortless" nature of AI-powered features
""",
    # Initialize empty artifact lists
    "final_select_ad_copies": {"final_select_ad_copies": []},
    "final_select_vis_concepts": {"final_select_vis_concepts": []},
    "img_artifact_keys": {"img_artifact_keys": []},
    "vid_artifact_keys": {"vid_artifact_keys": []},
    "combined_web_search_insights": "",
    "campaign_web_search_insights": "",
    "gs_web_search_insights": "",
    "yt_web_search_insights": "",
    "sources": {},
    "final_report_with_citations": "",
}


async def run_test():
    from trends_and_insights_agent.agent import root_agent

    runner = InMemoryRunner(
        agent=root_agent,
        app_name="test_ad_creative",
    )

    # Create session with pre-populated state
    session = await runner.session_service.create_session(
        app_name="test_ad_creative",
        user_id="test_user",
        state=MOCK_STATE,
    )
    session_id = session.id
    print(f"\nSession created: {session_id}")
    print(f"GCS folder: {session.state.get('gcs_folder', 'NOT SET')}")

    async def send_message(msg: str, step_name: str) -> list:
        print(f"\n{'='*60}")
        print(f"STEP: {step_name}")
        print(f"SENDING: {msg[:120]}...")
        print(f"{'='*60}")

        content = types.Content(
            parts=[types.Part(text=msg)],
            role="user",
        )

        events = []
        start = time.time()
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=content,
        ):
            events.append(event)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        preview = part.text[:300]
                        print(f"  [{event.author}]: {preview}")
                    elif part.function_call:
                        print(f"  [{event.author}] -> tool: {part.function_call.name}")
                    elif part.function_response:
                        print(f"  [{event.author}] <- tool response: {part.function_response.name}")
        elapsed = time.time() - start
        print(f"  Elapsed: {elapsed:.1f}s | Events: {len(events)}")
        return events

    def check_state():
        # Reload session to get latest state
        import asyncio
        session_latest = asyncio.get_event_loop().run_until_complete(
            runner.session_service.get_session(
                app_name="test_ad_creative",
                user_id="test_user",
                session_id=session_id,
            )
        )
        state = dict(session_latest.state) if session_latest.state else {}

        imgs = state.get("img_artifact_keys", {})
        vids = state.get("vid_artifact_keys", {})
        if isinstance(imgs, dict):
            imgs = imgs.get("img_artifact_keys", [])
        if isinstance(vids, dict):
            vids = vids.get("vid_artifact_keys", [])

        report_len = len(state.get("combined_final_cited_report", ""))
        ad_copies = state.get("final_select_ad_copies", {})
        if isinstance(ad_copies, dict):
            ad_copies = ad_copies.get("final_select_ad_copies", [])
        vis_concepts = state.get("final_select_vis_concepts", {})
        if isinstance(vis_concepts, dict):
            vis_concepts = vis_concepts.get("final_select_vis_concepts", [])

        print(f"\n--- State Check ---")
        print(f"  Research report: {report_len} chars")
        print(f"  Selected ad copies: {len(ad_copies)}")
        print(f"  Selected vis concepts: {len(vis_concepts)}")
        print(f"  Images: {len(imgs)}")
        print(f"  Videos: {len(vids)}")
        if imgs:
            for img in imgs:
                print(f"    IMG: {img.get('artifact_key', '?')}")
        if vids:
            for vid in vids:
                print(f"    VID: {vid.get('artifact_key', '?')}")
        print(f"  GCS folder: {state.get('gcs_folder', 'NOT SET')}")

        return {
            "num_ad_copies": len(ad_copies),
            "num_vis_concepts": len(vis_concepts),
            "num_images": len(imgs),
            "num_videos": len(vids),
            "gcs_folder": state.get("gcs_folder", ""),
        }

    # Step 1: Transfer to ad content generator with autopilot instructions
    await send_message(
        "Campaign metadata and research are already loaded. "
        "Transfer to the ad_content_generator_agent now. "
        "Generate ad creatives - select the top 2 ad ideas, create visual concepts for each, "
        "and present the draft report for my approval. Do not wait for my input on ad copy "
        "or visual concept selection - pick the best 2 automatically. "
        "When the draft report is ready, present it to me.",
        "Transfer to Ad Content Generator"
    )
    status = check_state()

    # Step 2: If the agent is waiting for approval, approve
    if status["num_ad_copies"] > 0 or status["num_vis_concepts"] > 0:
        await send_message(
            "The draft report looks great! I approve these 2 ad ideas. "
            "Proceed to generate the keyframe images and videos using reference images. "
            "For each concept: first generate the keyframe image, then use it as a reference "
            "image for video generation.",
            "Approve & Generate Creatives"
        )
        status = check_state()

    # Step 3: Follow-up if needed
    if status["num_images"] == 0:
        await send_message(
            "Please continue generating the visual creatives. For each concept, "
            "use generate_image first to create the keyframe, then use that image's "
            "artifact_key as existing_image_filename in generate_video.",
            "Follow-up: Generate Creatives"
        )
        status = check_state()

    # Verify GCS
    gcs_folder = status["gcs_folder"]
    if gcs_folder:
        print(f"\n--- GCS Verification ---")
        import subprocess
        result = subprocess.run(
            ["gsutil", "ls", f"gs://zghost-media-center/{gcs_folder}/"],
            capture_output=True, text=True
        )
        print(f"  GCS contents for {gcs_folder}/:")
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")

    # Final summary
    print(f"\n{'='*60}")
    print("AD CREATIVE E2E TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Selected ad copies: {status['num_ad_copies']} {'PASS' if status['num_ad_copies'] >= 2 else 'FAIL'}")
    print(f"  Selected vis concepts: {status['num_vis_concepts']} {'PASS' if status['num_vis_concepts'] >= 2 else 'FAIL'}")
    print(f"  Images generated: {status['num_images']} {'PASS' if status['num_images'] >= 2 else 'FAIL'}")
    print(f"  Videos generated: {status['num_videos']} {'PASS' if status['num_videos'] >= 2 else 'FAIL'}")

    all_pass = (
        status["num_ad_copies"] >= 2
        and status["num_vis_concepts"] >= 2
        and status["num_images"] >= 2
        and status["num_videos"] >= 2
    )
    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)
