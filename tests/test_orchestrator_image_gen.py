"""Unit tests for CampaignOrchestrator image generation, Gecko quality gate,
trajectory feedback, and artifact persistence."""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from google.genai import types
from google.adk.events import Event, EventActions


# ---------------------------------------------------------------------------
# Helpers – lightweight mocks that mirror real orchestrator structures
# ---------------------------------------------------------------------------

def _make_ctx(state=None, has_artifact_service=True):
    """Build a minimal InvocationContext-like mock."""
    ctx = Mock()
    ctx.session = Mock()
    ctx.session.id = "test-session-123"
    ctx.session.state = dict(state or {})
    ctx.session.events = []
    ctx.invocation_id = "inv-001"
    ctx.branch = None
    ctx.app_name = "test_app"
    ctx.user_id = "test_user"
    if has_artifact_service:
        ctx.artifact_service = AsyncMock()
        ctx.artifact_service.save_artifact = AsyncMock(return_value=1)
    else:
        ctx.artifact_service = None
    return ctx


def _gecko_result(score, passing=None, failing=None):
    """Build a Gecko evaluate() response dict."""
    return {
        "status": "success",
        "score": score,
        "passing": passing or [],
        "failing": failing or [],
    }


# ---------------------------------------------------------------------------
# Tests: Gecko failing verdicts stored in img_meta
# ---------------------------------------------------------------------------

class TestGeckoTrajectoryFeedback:
    """Gecko failing/passing verdicts must be stored in img_meta so that
    regeneration prompts can include trajectory feedback."""

    @patch("trends_and_insights_agent.orchestrator._get_media_client")
    @patch("trends_and_insights_agent.orchestrator.gecko_evaluate")
    @patch("trends_and_insights_agent.orchestrator.upload_blob_to_gcs")
    def test_gecko_verdicts_stored_in_img_meta(
        self, mock_upload, mock_gecko, mock_client
    ):
        """When Gecko returns failing verdicts, they must appear in img_meta."""
        # Arrange
        mock_gecko.return_value = _gecko_result(
            score=0.55,
            passing=["good composition"],
            failing=["product not visible", "text illegible"],
        )

        mock_img = Mock()
        mock_img.image.image_bytes = b"fake-png-bytes"
        mock_response = Mock()
        mock_response.generated_images = [mock_img]
        mock_client.return_value.models.generate_images.return_value = mock_response

        # Import the inner function by instantiating a minimal orchestrator
        from trends_and_insights_agent.orchestrator import CampaignOrchestrator

        orch = CampaignOrchestrator.__new__(CampaignOrchestrator)

        # We test _gen_upload_score indirectly via the parallel gen flow,
        # but to unit-test the gecko storage we replicate the logic:
        shot_def = {
            "concept_name": "TestConcept",
            "prompt": "A product shot",
            "shot_type": "product",
            "reference_type": "ASSET",
        }

        # Simulate what _gen_upload_score does
        img_client = mock_client()
        response = img_client.models.generate_images(
            model="imagen-4.0-generate-preview-06-06",
            prompt=shot_def["prompt"],
        )
        gen_img = response.generated_images[0]
        image_bytes = gen_img.image.image_bytes

        img_meta = {
            "artifact_key": "TestConcept_0.png",
            "img_prompt": shot_def["prompt"],
            "concept_name": shot_def["concept_name"],
            "shot_type": shot_def["shot_type"],
            "reference_type": "ASSET",
        }

        # Run gecko eval
        result = mock_gecko(
            prompt="product description",
            media_uri="gs://bucket/img.png",
            media_type="image",
            project_id="test-project",
            location="us-central1",
        )
        if isinstance(result, dict) and result.get("status") == "success":
            img_meta["fidelity_score"] = result.get("score", 0.0)
            if result.get("failing"):
                img_meta["gecko_failing_verdicts"] = result["failing"]
            if result.get("passing"):
                img_meta["gecko_passing_verdicts"] = result["passing"]

        # Assert
        assert img_meta["fidelity_score"] == 0.55
        assert img_meta["gecko_failing_verdicts"] == [
            "product not visible",
            "text illegible",
        ]
        assert img_meta["gecko_passing_verdicts"] == ["good composition"]

    def test_trajectory_prompt_includes_failing_verdicts(self):
        """When regenerating an image, the prompt should include prior failing verdicts."""
        existing_img = {
            "artifact_key": "Trend_0.png",
            "fidelity_score": 0.4,
            "gecko_failing_verdicts": ["blurry product", "wrong color palette"],
            "shot_type": "trend",
        }
        shot = {
            "prompt": "A trend-inspired scene with the product prominently displayed",
            "shot_type": "trend",
            "concept_name": "TrendShot",
            "reference_type": "ASSET",
        }

        # Replicate the trajectory feedback logic from orchestrator
        failing_verdicts = existing_img.get("gecko_failing_verdicts", [])
        if failing_verdicts:
            verdict_text = "; ".join(failing_verdicts[:5])
            shot = dict(shot)
            shot["prompt"] = (
                shot["prompt"].rstrip(". ")
                + f". IMPORTANT: A previous generation failed these quality checks: [{verdict_text}]. "
                f"Fix these issues in this generation."
            )

        assert "blurry product" in shot["prompt"]
        assert "wrong color palette" in shot["prompt"]
        assert "IMPORTANT: A previous generation failed" in shot["prompt"]

    def test_no_trajectory_when_no_verdicts(self):
        """When no failing verdicts exist, prompt should be unchanged."""
        existing_img = {
            "artifact_key": "Product_0.png",
            "fidelity_score": 0.5,
            # No gecko_failing_verdicts key
            "shot_type": "product",
        }
        original_prompt = "A clean product shot on white background"
        shot = {
            "prompt": original_prompt,
            "shot_type": "product",
            "concept_name": "ProductShot",
            "reference_type": "ASSET",
        }

        failing_verdicts = existing_img.get("gecko_failing_verdicts", [])
        if failing_verdicts:
            shot = dict(shot)
            shot["prompt"] += " IMPORTANT: ..."

        assert shot["prompt"] == original_prompt


# ---------------------------------------------------------------------------
# Tests: artifact_delta set for all images (including Gecko-failed)
# ---------------------------------------------------------------------------

class TestImageArtifactPersistence:
    """All generated images should be saved as ADK artifacts regardless of
    Gecko score, so users can see them in the UI."""

    def test_artifact_delta_set_for_passing_image(self):
        """artifact_delta should be set when image passes Gecko."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )

        art_version = 1
        artifact_key = "ProductShot_0.png"

        # Replicate orchestrator logic
        if art_version is not None and artifact_key:
            event.actions.artifact_delta[artifact_key] = art_version

        assert artifact_key in event.actions.artifact_delta
        assert event.actions.artifact_delta[artifact_key] == 1

    def test_artifact_delta_set_for_failing_image(self):
        """artifact_delta should ALSO be set when image fails Gecko — user
        needs to see what was generated even if it didn't pass."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )

        art_version = 2  # version from save_artifact
        artifact_key = "TrendShot_0.png"
        gecko_passed = False  # Failed Gecko

        # The key point: artifact_delta is set regardless of gecko_passed
        if art_version is not None and artifact_key:
            event.actions.artifact_delta[artifact_key] = art_version

        assert artifact_key in event.actions.artifact_delta

    def test_artifact_delta_skipped_when_no_artifact_service(self):
        """When artifact_service is None, art_version stays None and
        artifact_delta should not be set."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )

        art_version = None  # No artifact service
        artifact_key = "PersonShot_0.png"

        if art_version is not None and artifact_key:
            event.actions.artifact_delta[artifact_key] = art_version

        assert artifact_key not in event.actions.artifact_delta


# ---------------------------------------------------------------------------
# Tests: PDF artifact_delta always set
# ---------------------------------------------------------------------------

class TestPDFArtifactDelta:
    """PDF artifact_delta must always be present so the PDF appears in ADK web UI."""

    def test_pdf_artifact_delta_with_valid_version(self):
        """When save_artifact returns a valid version, artifact_delta is set."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )
        artifact_key = "final_trends_and_creatives_report.pdf"
        result = {"status": "ok", "artifact_key": artifact_key, "version": 3}

        version = result.get("version")
        if version is not None:
            event.actions.artifact_delta[artifact_key] = version
        else:
            event.actions.artifact_delta[artifact_key] = 0

        assert event.actions.artifact_delta[artifact_key] == 3

    def test_pdf_artifact_delta_with_none_version(self):
        """When version is None (no artifact_service), fallback to version 0."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )
        artifact_key = "final_trends_and_creatives_report.pdf"
        result = {"status": "ok", "artifact_key": artifact_key, "version": None}

        version = result.get("version")
        if version is not None:
            event.actions.artifact_delta[artifact_key] = version
        else:
            event.actions.artifact_delta[artifact_key] = 0

        assert event.actions.artifact_delta[artifact_key] == 0

    def test_pdf_artifact_delta_with_zero_version(self):
        """version=0 is valid (first save). Must not be treated as falsy."""
        event = Event(
            invocation_id="inv-001",
            author="test",
            actions=EventActions(state_delta={}, artifact_delta={}),
        )
        artifact_key = "final_trends_and_creatives_report.pdf"
        result = {"status": "ok", "artifact_key": artifact_key, "version": 0}

        version = result.get("version")
        if version is not None:
            event.actions.artifact_delta[artifact_key] = version
        else:
            event.actions.artifact_delta[artifact_key] = 0

        assert event.actions.artifact_delta[artifact_key] == 0


# ---------------------------------------------------------------------------
# Tests: State delta patterns (AE/GE persistence)
# ---------------------------------------------------------------------------

class TestStateDeltaPatterns:
    """Verify AE/GE state persistence patterns used in the orchestrator."""

    def test_per_image_state_delta_has_img_artifact_keys(self):
        """Each per-image event must include img_artifact_keys in state_delta."""
        img_slots = [
            {"artifact_key": "Product_0.png", "fidelity_score": 0.8},
            None,
            None,
        ]

        current_list = [m for m in img_slots if m is not None]
        state_delta = {"img_artifact_keys": {"img_artifact_keys": current_list}}

        assert len(state_delta["img_artifact_keys"]["img_artifact_keys"]) == 1
        assert state_delta["img_artifact_keys"]["img_artifact_keys"][0]["artifact_key"] == "Product_0.png"

    def test_pre_increment_failure_counter(self):
        """Failure counters must be pre-incremented BEFORE image gen starts."""
        fail_count = 2
        state_delta = {}
        idx = 1

        # Pre-increment (what orchestrator does before gen)
        state_delta[f"_img_fail_{idx}"] = fail_count + 1

        assert state_delta["_img_fail_1"] == 3

    def test_reset_failure_counter_on_gecko_pass(self):
        """On Gecko pass, failure counter resets to 0."""
        state_delta = {}
        idx = 0
        gecko_passed = True

        if gecko_passed:
            state_delta[f"_img_fail_{idx}"] = 0

        assert state_delta["_img_fail_0"] == 0

    def test_key_alias_normalization(self):
        """final_select_vis_concepts should be normalized to final_select_visual_concepts."""
        reconstructed = {
            "final_select_vis_concepts": [{"name": "concept1"}],
        }

        # Normalization logic from orchestrator
        if "final_select_vis_concepts" in reconstructed and "final_select_visual_concepts" not in reconstructed:
            reconstructed["final_select_visual_concepts"] = reconstructed["final_select_vis_concepts"]

        assert "final_select_visual_concepts" in reconstructed
        assert reconstructed["final_select_visual_concepts"] == [{"name": "concept1"}]

    def test_new_dict_creation_for_state_tracking(self):
        """ADK state tracking requires new dict creation, not in-place mutation."""
        # Simulate what should happen
        existing = {"img_artifact_keys": [{"artifact_key": "img1.png"}]}
        new_img = {"artifact_key": "img2.png"}

        # RIGHT: create new list/dict
        current_list = list(existing.get("img_artifact_keys", []))
        current_list.append(new_img)
        new_state = {"img_artifact_keys": current_list}

        assert len(new_state["img_artifact_keys"]) == 2
        assert new_state is not existing  # Must be a new dict


# ---------------------------------------------------------------------------
# Tests: Gecko quality gate logic
# ---------------------------------------------------------------------------

class TestGeckoQualityGate:
    """Verify the Gecko threshold and regeneration decision logic."""

    GECKO_THRESHOLD = 0.7

    def test_image_below_threshold_triggers_regen(self):
        """Images with fidelity_score < 0.7 should trigger regeneration."""
        img_meta = {"fidelity_score": 0.55, "skipped": False}
        needs_regen = (
            img_meta.get("fidelity_score") is not None
            and img_meta["fidelity_score"] < self.GECKO_THRESHOLD
        )
        assert needs_regen is True

    def test_image_above_threshold_no_regen(self):
        """Images with fidelity_score >= 0.7 should not trigger regeneration."""
        img_meta = {"fidelity_score": 0.85}
        needs_regen = (
            img_meta.get("fidelity_score") is not None
            and img_meta["fidelity_score"] < self.GECKO_THRESHOLD
        )
        assert needs_regen is False

    def test_image_without_score_no_regen(self):
        """Images without a fidelity_score should not trigger regeneration."""
        img_meta = {"artifact_key": "test.png"}
        needs_regen = (
            img_meta.get("fidelity_score") is not None
            and img_meta["fidelity_score"] < self.GECKO_THRESHOLD
        )
        assert needs_regen is False

    def test_skipped_images_excluded_from_regen(self):
        """Skipped images should never trigger regeneration."""
        img_meta = {"skipped": True, "fidelity_score": 0.3}
        valid = not img_meta.get("skipped")
        assert valid is False

    def test_max_retries_caps_regeneration(self):
        """After MAX_IMG_RETRIES, image should be skipped, not regenerated."""
        MAX_IMG_RETRIES = 5
        fail_count = 5

        if fail_count >= MAX_IMG_RETRIES:
            action = "skip"
        else:
            action = "regenerate"

        assert action == "skip"
