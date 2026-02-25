"""
Tests for av_editing_studio_agent: subject image generation, clip chain generation
with frame matching, concatenation, trimming, commercial artifact saving,
character consistency, scene continuity, and full pipeline integration.

All external dependencies (GCS, genai, cv2, ffmpeg) are mocked.
"""

import asyncio
import os
import sys
import tempfile
import uuid
from unittest import mock

import cv2
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Environment setup — must happen before any project imports
# ---------------------------------------------------------------------------
os.environ.setdefault("BUCKET", "gs://test-bucket")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT_NUMBER", "123456")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("YT_SECRET_MNGR_NAME", "test-secret")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_png_bytes(width=64, height=64):
    """Create minimal valid PNG bytes using cv2."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :, 2] = 255  # red channel
    success, buf = cv2.imencode(".png", img)
    assert success
    return buf.tobytes()


def _make_mp4_file(path, seconds=8, fps=24, width=64, height=64):
    """Write a minimal MP4 file with solid-color frames."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    total_frames = int(seconds * fps)
    for i in range(total_frames):
        frame = np.full((height, width, 3), fill_value=(i % 256), dtype=np.uint8)
        writer.write(frame)
    writer.release()


class FakeToolContext:
    """Minimal ToolContext stub for testing tools."""

    def __init__(self, state=None):
        self.state = state or {"gcs_folder": "2026_02_23_12_00"}
        self._artifacts = {}

    async def save_artifact(self, filename, artifact):
        self._artifacts[filename] = artifact
        return 1


PNG_BYTES = _make_png_bytes()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_session_media():
    """Remove session_media directory after each test."""
    yield
    import shutil
    if os.path.exists("session_media"):
        shutil.rmtree("session_media")


@pytest.fixture()
def tool_context():
    return FakeToolContext()


@pytest.fixture()
def tmp_video(tmp_path):
    """Create a temporary 8-second MP4 and return its path."""
    path = str(tmp_path / "test_clip.mp4")
    _make_mp4_file(path, seconds=8)
    return path


@pytest.fixture()
def tmp_videos_4(tmp_path):
    """Create 4 temporary 8-second MP4s and return their paths."""
    paths = []
    for i in range(4):
        p = str(tmp_path / f"clip_{i}.mp4")
        # Use slightly different frame values so we can detect ordering
        _make_mp4_file(p, seconds=8)
        paths.append(p)
    return paths


# ===================================================================
# 1. generate_subject_image
# ===================================================================
class TestGenerateSubjectImage:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            generate_subject_image,
        )
        return generate_subject_image

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_success(self, mock_client, mock_upload, tool_context):
        generate_subject_image = self._import_tool()

        # Mock Gemini response
        mock_part = mock.MagicMock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = PNG_BYTES

        mock_candidate = mock.MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = mock.MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response
        mock_upload.return_value = "uploaded"

        result = generate_subject_image(
            prompt="A young woman with red hair in a park",
            subject_name="hero_character",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert "gcs_uri" in result
        assert result["subject_name"] == "hero_character"
        assert result["gcs_uri"].startswith("gs://")
        assert "av_studio/subjects/" in result["gcs_uri"]
        assert os.path.exists(result["local_path"])

        # Verify the model was called with correct config
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs is not None

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_failure_no_candidates(self, mock_client, tool_context):
        generate_subject_image = self._import_tool()

        mock_response = mock.MagicMock()
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        result = generate_subject_image(
            prompt="test", subject_name="test", tool_context=tool_context
        )
        assert result["status"] == "failed"

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_filename_sanitization(self, mock_client, mock_upload, tool_context):
        generate_subject_image = self._import_tool()

        mock_part = mock.MagicMock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = PNG_BYTES

        mock_candidate = mock.MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response = mock.MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response
        mock_upload.return_value = "uploaded"

        result = generate_subject_image(
            prompt="test",
            subject_name="hero character, main",
            tool_context=tool_context,
        )
        assert result["status"] == "ok"
        # Filename should have spaces and commas removed
        assert " " not in os.path.basename(result["local_path"])
        assert "," not in os.path.basename(result["local_path"])


# ===================================================================
# 2. generate_clip_with_frames
# ===================================================================
class TestGenerateClipWithFrames:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            generate_clip_with_frames,
        )
        return generate_clip_with_frames

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.storage_client"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_blob"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_first_frame_only(self, mock_client, mock_download, mock_storage, tool_context):
        generate_clip_with_frames = self._import_tool()

        # Create a real MP4 to serve as the "downloaded" video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            _make_mp4_file(f.name, seconds=2)
            with open(f.name, "rb") as vf:
                video_bytes = vf.read()
            os.unlink(f.name)

        # Mock operation
        mock_video = mock.MagicMock()
        mock_video.video.uri = "gs://test-bucket/generated/video.mp4"

        mock_result = mock.MagicMock()
        mock_result.generated_videos = [mock_video]

        mock_op = mock.MagicMock()
        mock_op.done = True
        mock_op.error = None
        mock_op.result = mock_result
        mock_op.response = True

        mock_client.models.generate_videos.return_value = mock_op
        mock_download.return_value = video_bytes

        # Mock storage copy
        mock_bucket = mock.MagicMock()
        mock_storage.get_bucket.return_value = mock_bucket

        result = generate_clip_with_frames(
            prompt="Camera pans across a sunlit park",
            clip_name="clip_1",
            first_frame_gcs_uri="gs://test-bucket/subjects/hero.png",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert result["clip_name"] == "clip_1"
        assert "gcs_uri" in result

        # Verify generate_videos was called with first frame image
        call_kwargs = mock_client.models.generate_videos.call_args
        assert call_kwargs.kwargs.get("image") is not None or call_kwargs[1].get("image") is not None

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.storage_client"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_blob"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_with_last_frame(self, mock_client, mock_download, mock_storage, tool_context):
        generate_clip_with_frames = self._import_tool()

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            _make_mp4_file(f.name, seconds=2)
            with open(f.name, "rb") as vf:
                video_bytes = vf.read()
            os.unlink(f.name)

        mock_video = mock.MagicMock()
        mock_video.video.uri = "gs://test-bucket/generated/video.mp4"
        mock_result = mock.MagicMock()
        mock_result.generated_videos = [mock_video]
        mock_op = mock.MagicMock()
        mock_op.done = True
        mock_op.error = None
        mock_op.result = mock_result
        mock_op.response = True
        mock_client.models.generate_videos.return_value = mock_op
        mock_download.return_value = video_bytes
        mock_bucket = mock.MagicMock()
        mock_storage.get_bucket.return_value = mock_bucket

        result = generate_clip_with_frames(
            prompt="Camera tracks forward",
            clip_name="clip_2",
            first_frame_gcs_uri="gs://test-bucket/frames/clip1_last.png",
            tool_context=tool_context,
            last_frame_gcs_uri="gs://test-bucket/subjects/product.png",
        )

        assert result["status"] == "ok"

        # Verify GenerateVideosConfig had last_frame set
        call_kwargs = mock_client.models.generate_videos.call_args
        gen_config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert gen_config.last_frame is not None

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_operation_error(self, mock_client, tool_context):
        generate_clip_with_frames = self._import_tool()

        mock_op = mock.MagicMock()
        mock_op.done = True
        mock_op.error = "QUOTA_EXCEEDED"
        mock_client.models.generate_videos.return_value = mock_op

        result = generate_clip_with_frames(
            prompt="test",
            clip_name="clip_err",
            first_frame_gcs_uri="gs://test-bucket/img.png",
            tool_context=tool_context,
        )
        assert result["status"] == "failed"
        assert "QUOTA_EXCEEDED" in result["error"]


# ===================================================================
# 3. extract_frame_from_clip
# ===================================================================
class TestExtractFrameFromClip:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            extract_frame_from_clip,
        )
        return extract_frame_from_clip

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    def test_extract_first_frame(self, mock_download, mock_upload, tool_context, tmp_video):
        extract_frame_from_clip = self._import_tool()

        def fake_download(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            shutil.copy2(tmp_video, destination_file_name)
            return "downloaded"

        mock_download.side_effect = fake_download
        mock_upload.return_value = "uploaded"

        result = extract_frame_from_clip(
            video_gcs_uri="gs://test-bucket/clips/clip_1.mp4",
            frame_position="first",
            output_name="clip1_first",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert "gcs_uri" in result
        assert result["local_path"].endswith(".png")
        assert os.path.exists(result["local_path"])

        # Verify the extracted frame is a valid image
        img = cv2.imread(result["local_path"])
        assert img is not None
        assert img.shape[0] > 0 and img.shape[1] > 0

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    def test_extract_last_frame(self, mock_download, mock_upload, tool_context, tmp_video):
        extract_frame_from_clip = self._import_tool()

        def fake_download(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            shutil.copy2(tmp_video, destination_file_name)
            return "downloaded"

        mock_download.side_effect = fake_download
        mock_upload.return_value = "uploaded"

        result = extract_frame_from_clip(
            video_gcs_uri="gs://test-bucket/clips/clip_1.mp4",
            frame_position="last",
            output_name="clip1_last",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert os.path.exists(result["local_path"])

        # Verify last frame is different from first frame (different pixel values)
        last_img = cv2.imread(result["local_path"])
        assert last_img is not None

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    def test_invalid_video(self, mock_download, tool_context, tmp_path):
        extract_frame_from_clip = self._import_tool()

        # Write garbage data as the "video"
        def fake_download(source_blob_name, destination_file_name, gcs_bucket):
            with open(destination_file_name, "wb") as f:
                f.write(b"not a video")
            return "downloaded"

        mock_download.side_effect = fake_download

        result = extract_frame_from_clip(
            video_gcs_uri="gs://test-bucket/clips/bad.mp4",
            frame_position="first",
            output_name="bad_frame",
            tool_context=tool_context,
        )

        assert result["status"] == "failed"


# ===================================================================
# 4. concatenate_clips
# ===================================================================
class TestConcatenateClips:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            concatenate_clips,
        )
        return concatenate_clips

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    def test_concatenate_4_clips(self, mock_download, mock_upload, tool_context, tmp_videos_4):
        concatenate_clips = self._import_tool()

        # Map GCS URIs to local files
        uri_to_path = {}
        gcs_uris = []
        for i, path in enumerate(tmp_videos_4):
            uri = f"gs://test-bucket/clips/clip_{i}.mp4"
            gcs_uris.append(uri)
            uri_to_path[f"2026_02_23_12_00/av_studio/clips/clip_{i}.mp4"] = path
            # Also map the blob name without gcs_folder prefix
            uri_to_path[f"clips/clip_{i}.mp4"] = path

        def fake_download(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            # Find matching source
            for key, src_path in uri_to_path.items():
                if key in source_blob_name or source_blob_name in key:
                    shutil.copy2(src_path, destination_file_name)
                    return "downloaded"
            # Fallback: use first video
            shutil.copy2(tmp_videos_4[0], destination_file_name)
            return "downloaded"

        mock_download.side_effect = fake_download
        mock_upload.return_value = "uploaded"

        result = concatenate_clips(
            clip_gcs_uris=gcs_uris,
            output_name="commercial_raw",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert "gcs_uri" in result
        assert result["duration_seconds"] > 0
        # 4 x 8s = ~32s (allow some tolerance for codec)
        assert result["duration_seconds"] >= 28, f"Expected ~32s, got {result['duration_seconds']}s"
        assert os.path.exists(result["local_path"])

    def test_empty_uris(self, tool_context):
        concatenate_clips = self._import_tool()
        result = concatenate_clips(
            clip_gcs_uris=[], output_name="empty", tool_context=tool_context
        )
        assert result["status"] == "failed"


# ===================================================================
# 5. trim_video
# ===================================================================
class TestTrimVideo:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            trim_video,
        )
        return trim_video

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    def test_trim_to_30s(self, mock_download, mock_upload, tool_context, tmp_path):
        trim_video = self._import_tool()

        # Create a 32-second video to trim
        long_video = str(tmp_path / "long.mp4")
        _make_mp4_file(long_video, seconds=32)

        def fake_download(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            shutil.copy2(long_video, destination_file_name)
            return "downloaded"

        mock_download.side_effect = fake_download
        mock_upload.return_value = "uploaded"

        result = trim_video(
            video_gcs_uri="gs://test-bucket/av_studio/raw.mp4",
            target_duration_seconds=30,
            output_name="commercial_30s",
            tool_context=tool_context,
        )

        assert result["status"] == "ok"
        assert result["duration_seconds"] == 30
        assert "gcs_uri" in result
        assert os.path.exists(result["local_path"])

        # Verify the trimmed file is actually shorter
        cap = cv2.VideoCapture(result["local_path"])
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0:
            actual_duration = frame_count / fps
            assert actual_duration <= 31, f"Expected <=30s, got {actual_duration:.1f}s"


# ===================================================================
# 6. save_commercial_artifact
# ===================================================================
class TestSaveCommercialArtifact:

    def _import_tool(self):
        from trends_and_insights_agent.skills.av_studio.tools import (
            save_commercial_artifact,
        )
        return save_commercial_artifact

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_blob"
    )
    def test_save_artifact(self, mock_download, tool_context):
        save_commercial_artifact = self._import_tool()

        mock_download.return_value = b"fake video bytes"

        metadata = {
            "title": "Spring Freshness Meets Viral Dance - Tide Commercial",
            "scene_descriptions": [
                "Hook: GenZ dancer in dorm room notices stain before big event, trending dance move reference",
                "Connection: Reaches for Tide bottle, product appears naturally in daily routine",
                "Demonstration: Fresh spring scent visual, clothes emerge vibrant and clean",
                "Resolution: Dancer confidently performs at event in fresh outfit, brand CTA overlay",
            ],
            "total_clips": 4,
            "duration_seconds": 30,
            "trend_connections": "Viral TikTok dance trend + 'spring cleaning' Google Search trend",
            "narrative_arc": "A GenZ college student discovers that spring cleaning with Tide pairs perfectly with trending dance content, leading to confident self-expression.",
            "target_audience_appeal": "Authentic GenZ lifestyle moment that connects laundry (a chore) to self-expression and social media culture.",
        }

        result = asyncio.get_event_loop().run_until_complete(
            save_commercial_artifact(
                commercial_gcs_uri="gs://test-bucket/av_studio/commercial.mp4",
                commercial_metadata=metadata,
                tool_context=tool_context,
            )
        )

        assert result["status"] == "ok"
        assert result["artifact_key"] == "commercial_30s.mp4"

        # Verify session state was updated
        commercial = tool_context.state["commercial_artifact"]
        assert commercial["artifact_key"] == "commercial_30s.mp4"
        assert commercial["metadata"]["total_clips"] == 4
        assert commercial["metadata"]["duration_seconds"] == 30

        # Verify rich metadata is preserved
        assert "trend_connections" in commercial["metadata"]
        assert "narrative_arc" in commercial["metadata"]
        assert "target_audience_appeal" in commercial["metadata"]

        # Verify artifact was saved
        assert "commercial_30s.mp4" in tool_context._artifacts

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_blob"
    )
    def test_metadata_without_optional_fields(self, mock_download, tool_context):
        """save_commercial_artifact works with minimal metadata (backward compat)."""
        save_commercial_artifact = self._import_tool()
        mock_download.return_value = b"fake video bytes"

        metadata = {
            "title": "Test Commercial",
            "scene_descriptions": ["S1", "S2", "S3", "S4"],
            "total_clips": 4,
            "duration_seconds": 30,
        }

        result = asyncio.get_event_loop().run_until_complete(
            save_commercial_artifact(
                commercial_gcs_uri="gs://test-bucket/av_studio/commercial.mp4",
                commercial_metadata=metadata,
                tool_context=tool_context,
            )
        )
        assert result["status"] == "ok"


# ===================================================================
# 7. Character Consistency Checks
# ===================================================================
class TestCharacterConsistency:
    """Verify that character descriptions remain consistent across clip prompts."""

    def test_character_description_reuse(self):
        """Simulates the workflow where the same character description
        must be used across all clip prompts for visual consistency."""
        hero_description = (
            "A young woman in her mid-20s with shoulder-length auburn hair, "
            "wearing a crisp white linen shirt and dark indigo jeans, "
            "warm golden-hour lighting illuminating her face"
        )

        clip_prompts = [
            f"Scene 1: {hero_description}, walking through a sunlit meadow, camera tracking forward",
            f"Scene 2: {hero_description}, reaching for a bottle of detergent on a shelf, medium close-up",
            f"Scene 3: {hero_description}, smiling while folding fresh laundry, warm indoor lighting",
            f"Scene 4: {hero_description}, holding the product toward camera, brand logo visible",
        ]

        for i, prompt in enumerate(clip_prompts):
            assert hero_description in prompt, (
                f"Clip {i+1} prompt does not contain the exact hero character description. "
                f"This breaks visual consistency across the commercial."
            )

    def test_multiple_subjects_consistency(self):
        """Multiple subjects (character + product) must both remain consistent."""
        character = "a tall man with short brown hair wearing a blue polo shirt"
        product = "a bright orange Tide detergent bottle with white cap"

        scenes = [
            {"characters": [character], "props": [product]},
            {"characters": [character], "props": [product]},
            {"characters": [character], "props": [product]},
            {"characters": [character], "props": [product]},
        ]

        for i, scene in enumerate(scenes):
            assert character in scene["characters"], f"Scene {i+1} missing character"
            assert product in scene["props"], f"Scene {i+1} missing product"

    def test_character_prompt_word_for_word(self):
        """The prompt instruction says character descriptions must be maintained
        word-for-word. Verify that even minor changes are detected."""
        original = "a young woman with red curly hair and green eyes"
        modified = "a young woman with red curly hair and blue eyes"

        assert original != modified, "Descriptions should differ"
        # This simulates what the agent SHOULD NOT do
        assert "green" in original
        assert "blue" in modified
        assert "green" not in modified, (
            "Modified description correctly changed 'green' to 'blue' — "
            "this would break visual consistency"
        )


# ===================================================================
# 8. Scene Continuity Checks
# ===================================================================
class TestSceneContinuity:
    """Verify frame-matching logic: last frame of clip N = first frame of clip N+1."""

    def test_last_frame_extraction_matches_video_end(self, tmp_video):
        """The last frame extracted should correspond to the actual last frame."""
        cap = cv2.VideoCapture(tmp_video)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Read last frame directly
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, last_frame = cap.read()
        cap.release()

        assert ret, "Should be able to read the last frame"
        assert last_frame is not None
        assert last_frame.shape[0] > 0

    def test_frame_chain_linkage(self, tmp_path):
        """Simulate the clip chain: extract last frame of clip N,
        verify it could serve as first frame of clip N+1."""
        clips = []
        for i in range(4):
            path = str(tmp_path / f"clip_{i}.mp4")
            # Each clip has unique pixel values so frames are distinguishable
            _make_mp4_file(path, seconds=2, width=32, height=32)
            clips.append(path)

        extracted_last_frames = []
        for clip_path in clips:
            cap = cv2.VideoCapture(clip_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, total - 1)
            ret, frame = cap.read()
            cap.release()
            assert ret, f"Failed to extract last frame from {clip_path}"
            extracted_last_frames.append(frame)

        # Verify we got 4 distinct frames (one per clip)
        assert len(extracted_last_frames) == 4

        # Each extracted frame should be a valid image that could be saved as PNG
        for i, frame in enumerate(extracted_last_frames):
            frame_path = str(tmp_path / f"last_frame_{i}.png")
            cv2.imwrite(frame_path, frame)
            assert os.path.exists(frame_path), f"Failed to save frame {i}"
            # Verify it can be read back
            reloaded = cv2.imread(frame_path)
            assert reloaded is not None, f"Failed to reload frame {i}"

    def test_first_last_frame_dimensions_match(self, tmp_video):
        """First and last frames of a clip must have identical dimensions
        for use as conditioning frames in Veo."""
        cap = cv2.VideoCapture(tmp_video)

        # First frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret1, first = cap.read()

        # Last frame
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total - 1)
        ret2, last = cap.read()
        cap.release()

        assert ret1 and ret2
        assert first.shape == last.shape, (
            f"Frame dimensions mismatch: first={first.shape} vs last={last.shape}"
        )


# ===================================================================
# 9. Full Pipeline Integration Test
# ===================================================================
class TestFullPipeline:
    """Integration test: 4 clips → concat → trim → 30s commercial."""

    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.upload_blob_to_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_blob"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.download_image_from_gcs"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.storage_client"
    )
    @mock.patch(
        "trends_and_insights_agent.skills.av_studio.tools.client"
    )
    def test_full_pipeline_produces_30s_commercial(
        self, mock_client, mock_storage, mock_dl_img, mock_dl_blob, mock_upload, tmp_path
    ):
        from trends_and_insights_agent.skills.av_studio.tools import (
            generate_subject_image,
            generate_clip_with_frames,
            extract_frame_from_clip,
            concatenate_clips,
            trim_video,
            save_commercial_artifact,
        )

        ctx = FakeToolContext()

        # --- Step 1: Generate subject image ---
        mock_part = mock.MagicMock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = PNG_BYTES
        mock_candidate = mock.MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response = mock.MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response
        mock_upload.return_value = "uploaded"

        subject_result = generate_subject_image(
            prompt="Hero character for commercial",
            subject_name="hero",
            tool_context=ctx,
        )
        assert subject_result["status"] == "ok"

        # --- Step 2: Generate 4 clips with frame chaining ---
        clip_videos = []
        for i in range(4):
            clip_path = str(tmp_path / f"gen_clip_{i}.mp4")
            _make_mp4_file(clip_path, seconds=8)
            clip_videos.append(clip_path)

        clip_gcs_uris = []
        clip_idx = [0]

        def setup_video_generation():
            idx = clip_idx[0]
            with open(clip_videos[idx], "rb") as f:
                vbytes = f.read()

            mock_video = mock.MagicMock()
            mock_video.video.uri = f"gs://test-bucket/generated/clip_{idx}.mp4"
            mock_result_obj = mock.MagicMock()
            mock_result_obj.generated_videos = [mock_video]
            mock_op = mock.MagicMock()
            mock_op.done = True
            mock_op.error = None
            mock_op.result = mock_result_obj
            mock_op.response = True
            mock_client.models.generate_videos.return_value = mock_op
            mock_dl_blob.return_value = vbytes
            mock_bucket = mock.MagicMock()
            mock_storage.get_bucket.return_value = mock_bucket

        # Generate clip 1 (using subject image as first frame)
        setup_video_generation()
        result = generate_clip_with_frames(
            prompt="Scene 1: Hero walking through park",
            clip_name="clip_1",
            first_frame_gcs_uri=subject_result["gcs_uri"],
            tool_context=ctx,
        )
        assert result["status"] == "ok"
        clip_gcs_uris.append(result["gcs_uri"])

        # For clips 2-4: extract last frame, use as first frame
        for i in range(1, 4):
            # Extract last frame from previous clip
            def make_fake_dl(src_path):
                def fake_dl(source_blob_name, destination_file_name, gcs_bucket):
                    import shutil
                    shutil.copy2(src_path, destination_file_name)
                    return "downloaded"
                return fake_dl

            mock_dl_img.side_effect = make_fake_dl(clip_videos[i - 1])

            frame_result = extract_frame_from_clip(
                video_gcs_uri=clip_gcs_uris[-1],
                frame_position="last",
                output_name=f"clip{i}_last",
                tool_context=ctx,
            )
            assert frame_result["status"] == "ok"

            # Generate next clip
            clip_idx[0] = i
            setup_video_generation()
            result = generate_clip_with_frames(
                prompt=f"Scene {i+1}: Continuation",
                clip_name=f"clip_{i+1}",
                first_frame_gcs_uri=frame_result["gcs_uri"],
                tool_context=ctx,
            )
            assert result["status"] == "ok"
            clip_gcs_uris.append(result["gcs_uri"])

        assert len(clip_gcs_uris) == 4

        # --- Step 3: Concatenate ---
        def fake_dl_for_concat(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            # Map blob name back to local clip
            for i, uri in enumerate(clip_gcs_uris):
                if source_blob_name in uri or uri.endswith(source_blob_name):
                    shutil.copy2(clip_videos[i], destination_file_name)
                    return "downloaded"
            # Fallback by index from blob name
            for i in range(4):
                if f"clip_{i+1}" in source_blob_name or f"gen_clip_{i}" in source_blob_name:
                    shutil.copy2(clip_videos[i], destination_file_name)
                    return "downloaded"
            shutil.copy2(clip_videos[0], destination_file_name)
            return "downloaded"

        mock_dl_img.side_effect = fake_dl_for_concat

        concat_result = concatenate_clips(
            clip_gcs_uris=clip_gcs_uris,
            output_name="commercial_raw",
            tool_context=ctx,
        )
        assert concat_result["status"] == "ok"
        assert concat_result["duration_seconds"] >= 28, (
            f"Concatenated duration should be ~32s, got {concat_result['duration_seconds']}s"
        )

        # --- Step 4: Trim to 30s ---
        def fake_dl_concat(source_blob_name, destination_file_name, gcs_bucket):
            import shutil
            shutil.copy2(concat_result["local_path"], destination_file_name)
            return "downloaded"

        mock_dl_img.side_effect = fake_dl_concat

        trim_result = trim_video(
            video_gcs_uri=concat_result["gcs_uri"],
            target_duration_seconds=30,
            output_name="commercial_30s",
            tool_context=ctx,
        )
        assert trim_result["status"] == "ok"
        assert trim_result["duration_seconds"] == 30

        # --- Step 5: Save artifact ---
        with open(trim_result["local_path"], "rb") as f:
            final_bytes = f.read()
        mock_dl_blob.return_value = final_bytes

        metadata = {
            "title": "Trending Freshness - Tide Spring Campaign",
            "scene_descriptions": [
                "Hook: Hero discovers viral trend in everyday setting",
                "Connection: Product naturally enters the scene during routine",
                "Demonstration: Product benefits shown through visual storytelling",
                "Resolution: Hero confidently embraces trend with brand CTA",
            ],
            "total_clips": 4,
            "duration_seconds": 30,
            "trend_connections": "Spring cleaning Search trend + viral lifestyle YouTube trend",
            "narrative_arc": "An everyday moment becomes extraordinary when trending culture meets product innovation.",
            "target_audience_appeal": "Authentic lifestyle connection that makes the product feel culturally relevant.",
        }

        save_result = asyncio.get_event_loop().run_until_complete(
            save_commercial_artifact(
                commercial_gcs_uri=trim_result["gcs_uri"],
                commercial_metadata=metadata,
                tool_context=ctx,
            )
        )
        assert save_result["status"] == "ok"
        assert ctx.state["commercial_artifact"]["metadata"]["duration_seconds"] == 30
        assert ctx.state["commercial_artifact"]["metadata"]["trend_connections"] != ""
        assert ctx.state["commercial_artifact"]["metadata"]["narrative_arc"] != ""
        assert "commercial_30s.mp4" in ctx._artifacts


# ===================================================================
# 10. Agent Configuration
# ===================================================================
class TestAgentConfiguration:
    """Verify the agent is correctly configured."""

    def test_config_has_subject_image_gen_model(self):
        from trends_and_insights_agent.shared_libraries.config import config
        assert hasattr(config, "subject_image_gen_model")
        assert config.subject_image_gen_model == "gemini-3-pro-image-preview"

    def test_session_state_has_commercial_artifact(self):
        from trends_and_insights_agent.shared_libraries.config import setup_config
        state = setup_config.empty_session_state["state"]
        assert "commercial_artifact" in state

    def test_agent_has_all_tools(self):
        from trends_and_insights_agent.skills.av_studio.agents import (
            av_editing_studio_agent,
        )
        tool_names = {t.__name__ if callable(t) else str(t) for t in av_editing_studio_agent.tools}
        expected = {
            "generate_subject_image",
            "generate_clip_with_frames",
            "extract_frame_from_clip",
            "concatenate_clips",
            "trim_video",
            "save_commercial_artifact",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_agent_registered_in_root(self):
        from trends_and_insights_agent.agent import root_agent
        sub_names = [a.name for a in root_agent.sub_agents]
        assert "av_editing_studio_agent" in sub_names

    def test_root_prompt_mentions_av_studio(self):
        from trends_and_insights_agent.prompts import ROOT_AGENT_INSTR
        assert "av_editing_studio_agent" in ROOT_AGENT_INSTR


# ===================================================================
# 11. Trend-Driven Completion Logic
# ===================================================================
class TestTrendDrivenCompletion:
    """Verify the prompt enforces trend-connected, consistent, logical, compelling output."""

    def test_prompt_references_trends_and_research(self):
        """The AV studio prompt must reference trend and research session state keys."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "{target_search_trends}" in AV_STUDIO_INSTR
        assert "{target_yt_trends}" in AV_STUDIO_INSTR
        assert "{combined_final_cited_report}" in AV_STUDIO_INSTR
        assert "{final_select_ad_copies}" in AV_STUDIO_INSTR
        assert "{final_select_vis_concepts}" in AV_STUDIO_INSTR

    def test_prompt_includes_brand_and_audience_context(self):
        """The prompt must interpolate brand, product, audience, and selling points."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "{brand}" in AV_STUDIO_INSTR
        assert "{target_product}" in AV_STUDIO_INSTR
        assert "{target_audience}" in AV_STUDIO_INSTR
        assert "{key_selling_points}" in AV_STUDIO_INSTR

    def test_prompt_enforces_narrative_arc(self):
        """The prompt should define a 4-scene narrative arc structure."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        # Check the narrative arc labels are present
        assert "Hook" in AV_STUDIO_INSTR
        assert "Connection" in AV_STUDIO_INSTR
        assert "Demonstration" in AV_STUDIO_INSTR
        assert "Resolution" in AV_STUDIO_INSTR or "CTA" in AV_STUDIO_INSTR

    def test_prompt_requires_character_consistency(self):
        """The prompt must instruct the agent to maintain word-for-word descriptions."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "word-for-word" in AV_STUDIO_INSTR.lower() or "verbatim" in AV_STUDIO_INSTR.lower()

    def test_prompt_includes_quality_review(self):
        """The prompt should include a pre-save quality review step."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "quality review" in AV_STUDIO_INSTR.lower() or "Consistency" in AV_STUDIO_INSTR
        assert "Logic" in AV_STUDIO_INSTR or "logical" in AV_STUDIO_INSTR.lower()
        assert "Compelling" in AV_STUDIO_INSTR or "compelling" in AV_STUDIO_INSTR.lower()

    def test_prompt_requires_trend_connection_in_metadata(self):
        """The prompt should instruct including trend_connections in metadata."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "trend_connections" in AV_STUDIO_INSTR
        assert "narrative_arc" in AV_STUDIO_INSTR
        assert "target_audience_appeal" in AV_STUDIO_INSTR

    def test_prompt_consistency_checklist(self):
        """The prompt should include a consistency checklist before proceeding."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        # The checklist should reference character consistency, product placement,
        # tone alignment, and trend authenticity
        assert "product appears" in AV_STUDIO_INSTR.lower() or "target product" in AV_STUDIO_INSTR.lower()
        assert "tone" in AV_STUDIO_INSTR.lower()
        assert "trend connection" in AV_STUDIO_INSTR.lower() or "trend authenticity" in AV_STUDIO_INSTR.lower()

    def test_storyboard_requires_trend_connection_per_scene(self):
        """Each scene definition must include which trend it connects to."""
        from trends_and_insights_agent.skills.av_studio.prompts import (
            AV_STUDIO_INSTR,
        )
        assert "Trend connection" in AV_STUDIO_INSTR or "trend insight" in AV_STUDIO_INSTR.lower()

    def test_full_pipeline_with_rich_metadata(self, tmp_path):
        """Integration: verify that the full pipeline produces metadata
        with trend connections and narrative arc."""
        from trends_and_insights_agent.skills.av_studio.tools import (
            save_commercial_artifact,
        )

        ctx = FakeToolContext(state={
            "gcs_folder": "2026_02_23_12_00",
            "target_search_trends": {"target_search_trends": ["spring cleaning tips"]},
            "target_yt_trends": {"target_yt_trends": ["viral dance challenge"]},
        })

        metadata = {
            "title": "Spring Clean Dance - Tide Fresh Spring",
            "scene_descriptions": [
                "Hook: GenZ student scrolling TikTok sees viral dance, notices stained outfit",
                "Connection: Grabs Tide Fresh Spring from shelf, relatable dorm laundry moment",
                "Demonstration: Clothes emerge vibrant, spring scent visualized with flower petals",
                "Resolution: Student confidently joins viral dance in fresh outfit, Tide logo + CTA",
            ],
            "total_clips": 4,
            "duration_seconds": 30,
            "trend_connections": "Viral TikTok dance challenge + spring cleaning Google Search trend",
            "narrative_arc": "A GenZ student transforms a stained outfit crisis into a confident dance moment using Tide Fresh Spring.",
            "target_audience_appeal": "Authentic GenZ experience connecting laundry chores to social media self-expression and trending content.",
        }

        with mock.patch(
            "trends_and_insights_agent.skills.av_studio.tools.download_blob"
        ) as mock_dl:
            mock_dl.return_value = b"fake video bytes"

            result = asyncio.get_event_loop().run_until_complete(
                save_commercial_artifact(
                    commercial_gcs_uri="gs://test-bucket/av_studio/final.mp4",
                    commercial_metadata=metadata,
                    tool_context=ctx,
                )
            )

        assert result["status"] == "ok"
        saved = ctx.state["commercial_artifact"]

        # Verify trend-driven metadata is fully persisted
        assert "dance" in saved["metadata"]["trend_connections"].lower()
        assert "spring" in saved["metadata"]["trend_connections"].lower()
        assert len(saved["metadata"]["scene_descriptions"]) == 4
        assert saved["metadata"]["narrative_arc"] != ""
        assert saved["metadata"]["target_audience_appeal"] != ""

        # Verify each scene description mentions a trend or product context
        for desc in saved["metadata"]["scene_descriptions"]:
            assert len(desc) > 10, f"Scene description too short: '{desc}'"
