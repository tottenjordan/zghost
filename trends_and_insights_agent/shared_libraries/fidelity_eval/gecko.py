"""Gecko rubric-based media fidelity evaluation.

Evaluates generated images and videos against ground-truth product descriptions
using Vertex AI's rubric-based Gecko metrics (GECKO_TEXT2IMAGE / GECKO_TEXT2VIDEO).
The evaluation generates per-attribute rubrics and returns a composite fidelity
score (0.0-1.0) along with individual passing/failing verdicts.

Based on Gecko: Versatile Text Embeddings Distilled from Large Language Models
    Jinhyuk Lee, Zhuyun Dai, Xiaoqi Ren, et al. (2024)
    https://arxiv.org/abs/2404.16820

Adapted from: https://github.com/behardja/product-fidelity-eval
    (branch: expand_video_feature) by Bryan Eusebio

References:
    Vertex AI rubric-based metrics:
        https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/metrics/rubric-based-metrics
    RubricMetric SDK reference:
        https://cloud.google.com/python/docs/reference/vertexai/latest/vertexai.types.RubricMetric
"""

import logging
import time

import pandas as pd
from google.genai.errors import ClientError
from vertexai import Client as VertexClient
from vertexai import types as vertex_types

logger = logging.getLogger("fidelity_eval.gecko")

RUBRIC_MAX_RETRIES = 3
RUBRIC_RETRY_DELAY = 10  # seconds

_MEDIA_CONFIG = {
    "image": {
        "mime_prefix": "image/png",
        "rubric_group": "gecko_image_rubrics",
        "rubric_metric": vertex_types.RubricMetric.GECKO_TEXT2IMAGE,
    },
    "video": {
        "mime_prefix": "video/mp4",
        "rubric_group": "gecko_video_rubrics",
        "rubric_metric": vertex_types.RubricMetric.GECKO_TEXT2VIDEO,
    },
}


def evaluate(
    prompt: str,
    media_uri: str,
    media_type: str,
    project_id: str,
    location: str,
) -> dict:
    """Run Gecko evaluation on a candidate image or video.

    Args:
        prompt: The ground-truth description to evaluate against.
        media_uri: GCS URI of the candidate media to evaluate.
        media_type: "image" or "video".
        project_id: GCP project ID.
        location: GCP region.

    Returns:
        dict with keys:
          - status: "success" or "error"
          - score: float (0.0-1.0)
          - total_verdicts: int
          - passing_count: int
          - failing_count: int
          - passing: list[str]  (passing verdict descriptions)
          - failing: list[str]  (failing verdict descriptions)
    """
    if media_type not in _MEDIA_CONFIG:
        raise ValueError(f"media_type must be 'image' or 'video', got '{media_type}'")

    cfg = _MEDIA_CONFIG[media_type]
    vertex_client = VertexClient(project=project_id, location=location)

    response_data = {
        "parts": [
            {"file_data": {"mime_type": cfg["mime_prefix"], "file_uri": media_uri}}
        ],
        "role": "model",
    }
    eval_dataset = pd.DataFrame(
        {"prompt": [prompt], "response": [response_data]}
    )

    # Generate rubrics with retry on rate-limit (429) errors
    data_with_rubrics = None
    for rubric_attempt in range(1, RUBRIC_MAX_RETRIES + 1):
        try:
            data_with_rubrics = vertex_client.evals.generate_rubrics(
                src=eval_dataset,
                rubric_group_name=cfg["rubric_group"],
                predefined_spec_name=cfg["rubric_metric"],
            )
            if isinstance(data_with_rubrics, pd.DataFrame):
                df = data_with_rubrics
            else:
                df = getattr(data_with_rubrics, "eval_dataset_df", None)
            if (
                df is not None
                and "rubric_groups" in df.columns
                and len(df) > 0
                and df["rubric_groups"].iloc[0]
            ):
                break
            logger.warning(
                "Rubric generation returned empty results "
                "(attempt %d/%d), retrying...",
                rubric_attempt,
                RUBRIC_MAX_RETRIES,
            )
            if rubric_attempt < RUBRIC_MAX_RETRIES:
                time.sleep(RUBRIC_RETRY_DELAY)
        except ClientError as e:
            if e.status_code == 429 and rubric_attempt < RUBRIC_MAX_RETRIES:
                logger.warning(
                    "Rubric generation rate-limited "
                    "(attempt %d/%d), retrying in %ds...",
                    rubric_attempt,
                    RUBRIC_MAX_RETRIES,
                    RUBRIC_RETRY_DELAY,
                )
                time.sleep(RUBRIC_RETRY_DELAY)
            else:
                raise

    # Evaluate
    eval_result = vertex_client.evals.evaluate(
        dataset=data_with_rubrics,
        metrics=[cfg["rubric_metric"]],
    )

    # Extract results
    case = eval_result.eval_case_results[0]
    metric_data = case.response_candidate_results[0].metric_results
    metric_key = list(metric_data.keys())[0]
    data = metric_data[metric_key]
    score = data.score
    verdicts = data.rubric_verdicts

    # Detect evaluation infrastructure failures
    if score is None and not verdicts:
        return {
            "status": "error",
            "message": (
                "Evaluation infrastructure error: no score or verdicts "
                "returned. This is likely due to a transient rate-limit "
                "on the judge model. Please retry."
            ),
        }

    score = score if score is not None else 0.0

    passing = []
    failing = []
    if verdicts:
        for v in verdicts:
            raw_verdict = getattr(v, "verdict", False)
            is_pass = str(raw_verdict).lower() == "true"
            try:
                text = v.evaluated_rubric.content.property.description
            except AttributeError:
                text = str(v)
            if is_pass:
                passing.append(text)
            else:
                failing.append(text)

    return {
        "status": "success",
        "score": score,
        "total_verdicts": len(passing) + len(failing),
        "passing_count": len(passing),
        "failing_count": len(failing),
        "passing": passing,
        "failing": failing,
    }
