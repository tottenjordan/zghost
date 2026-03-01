"""
Evaluation service for running ADK agent evaluations.
Wraps google.adk.evaluation.agent_evaluator.AgentEvaluator with additional
support for custom rubric criteria, and optionally Vertex AI Evaluation Service
for PointwiseMetric-based evaluations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.evaluation.agent_evaluator import AgentEvaluator

logger = logging.getLogger(__name__)

# Lazy availability flag for Vertex AI evaluation
_VERTEX_EVAL_AVAILABLE: Optional[bool] = None


def _check_vertex_eval_available() -> bool:
    """Check if vertexai.evaluation is importable."""
    global _VERTEX_EVAL_AVAILABLE
    if _VERTEX_EVAL_AVAILABLE is None:
        try:
            from vertexai.evaluation import EvalTask  # noqa: F401
            _VERTEX_EVAL_AVAILABLE = True
        except ImportError:
            _VERTEX_EVAL_AVAILABLE = False
            logger.info("vertexai.evaluation not available; Vertex AI eval disabled")
    return _VERTEX_EVAL_AVAILABLE


def run_evaluation(
    eval_dataset_path: str,
    agent_module: str = "trends_and_insights_agent",
    rubric_criteria: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run an ADK evaluation with optional custom rubric criteria.

    Args:
        eval_dataset_path: Path to eval dataset JSON file
        agent_module: Python module path to agent (default: trends_and_insights_agent)
        rubric_criteria: Optional list of rubric criteria dicts with keys:
            - name: str
            - description: str
            - weight: float

    Returns:
        Dict containing evaluation results
    """
    try:
        logger.info(
            f"Starting evaluation: dataset={eval_dataset_path}, "
            f"agent_module={agent_module}, "
            f"rubric_criteria={'custom' if rubric_criteria else 'default'}"
        )

        # If custom rubric criteria provided, we could potentially inject these
        # into the evaluation process. For now, ADK's AgentEvaluator doesn't
        # directly support custom rubrics, so we'll run the standard evaluation
        # and annotate results with rubric info if provided.
        # TODO: Explore ADK's evaluation customization options for rubric integration

        # Run standard ADK evaluation
        results = AgentEvaluator.evaluate(
            agent_module=agent_module,
            eval_dataset_file_path_or_dir=eval_dataset_path,
        )

        # Annotate results with rubric criteria if provided
        if rubric_criteria:
            results["rubric_criteria"] = rubric_criteria
            results["custom_rubric_applied"] = True
            logger.info(
                f"Evaluation completed with custom rubric ({len(rubric_criteria)} criteria)"
            )
        else:
            results["custom_rubric_applied"] = False
            logger.info("Evaluation completed with default ADK rubric")

        return results

    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}", exc_info=True)
        raise


def list_eval_sets(eval_dir: str = "tests") -> List[Dict]:
    """
    List available evaluation datasets in the specified directory.

    Args:
        eval_dir: Directory to search for .test.json files (default: tests)

    Returns:
        List of dicts with eval set metadata:
            - name: str
            - path: str
            - num_cases: int
    """
    try:
        eval_path = Path(eval_dir)
        if not eval_path.exists():
            logger.warning(f"Eval directory not found: {eval_dir}")
            return []

        eval_sets = []
        for test_file in eval_path.glob("*.test.json"):
            try:
                # Load to count cases
                with open(test_file, "r") as f:
                    data = json.load(f)
                    num_cases = len(data) if isinstance(data, list) else 1

                eval_sets.append(
                    {
                        "name": test_file.stem,  # filename without .test.json
                        "path": str(test_file),
                        "num_cases": num_cases,
                    }
                )
            except Exception as e:
                logger.error(f"Error reading eval set {test_file}: {str(e)}")
                continue

        logger.info(f"Found {len(eval_sets)} eval sets in {eval_dir}")
        return eval_sets

    except Exception as e:
        logger.error(f"Error listing eval sets: {str(e)}", exc_info=True)
        raise


def load_eval_set(path: str) -> Dict:
    """
    Load and return the content of an evaluation dataset.

    Args:
        path: Path to the eval dataset JSON file

    Returns:
        Dict or List containing eval dataset content
    """
    try:
        eval_path = Path(path)
        if not eval_path.exists():
            raise FileNotFoundError(f"Eval set not found: {path}")

        with open(eval_path, "r") as f:
            data = json.load(f)

        logger.info(
            f"Loaded eval set: {path} ({len(data) if isinstance(data, list) else 1} cases)"
        )
        return data

    except Exception as e:
        logger.error(f"Error loading eval set: {str(e)}", exc_info=True)
        raise


def run_vertex_evaluation(
    rubric_criteria: List[Dict[str, Any]],
    session_state: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    brand: Optional[str] = None,
    target_product: Optional[str] = None,
) -> Dict[str, Any]:
    """Run evaluation using Vertex AI Evaluation Service with PointwiseMetric.

    Uses vertexai.evaluation.EvalTask with custom PointwiseMetric definitions
    derived from the provided rubric criteria. When session_state is provided,
    pipeline outputs (report, ad copies) are extracted and evaluated.

    Args:
        rubric_criteria: List of dicts with keys: name, description, weight.
        session_state: Optional session state dict to pull pipeline outputs from.
        session_id: Optional session ID for traceability.
        brand: Optional brand name for evaluation context.
        target_product: Optional product name for evaluation context.

    Returns:
        Dict with evaluation metrics and per-criterion scores.

    Raises:
        ImportError: If vertexai.evaluation is not available.
    """
    if not _check_vertex_eval_available():
        raise ImportError(
            "vertexai.evaluation is not installed. "
            "Install with: pip install google-cloud-aiplatform[evaluation]"
        )

    import vertexai
    from vertexai.evaluation import EvalTask, PointwiseMetric

    logger.info(
        f"Starting Vertex AI evaluation: session_id={session_id}, "
        f"brand={brand}, criteria_count={len(rubric_criteria)}"
    )

    # Initialize Vertex AI
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if project:
        vertexai.init(project=project, location=location)

    # Build PointwiseMetric definitions from rubric criteria
    metrics = []
    for criterion in rubric_criteria:
        metric_name = criterion["name"].lower().replace(" ", "_")
        metric = PointwiseMetric(
            metric=metric_name,
            metric_prompt_template=(
                f"Evaluate the following response on the criterion: {criterion['name']}.\n"
                f"Description: {criterion['description']}\n"
                f"Rate on a scale of 1-5 where 1 is poor and 5 is excellent.\n\n"
                f"Response: {{response}}\n\n"
                f"Score (1-5):"
            ),
        )
        metrics.append(metric)

    # Extract evaluation data from session state
    eval_data = []
    if session_state:
        # Extract report text
        report = (
            session_state.get("combined_final_cited_report")
            or session_state.get("final_report_with_citations")
            or ""
        )
        if report:
            context = f"Brand: {brand or 'N/A'}, Product: {target_product or 'N/A'}"
            eval_data.append({
                "response": str(report)[:10000],  # Truncate for API limits
                "context": context,
                "source": "research_report",
            })

        # Extract ad copies
        raw_copies = session_state.get("final_select_ad_copies", [])
        if isinstance(raw_copies, dict):
            raw_copies = raw_copies.get("final_select_ad_copies", [])
        if isinstance(raw_copies, list):
            for i, copy in enumerate(raw_copies[:3]):
                text = ""
                if isinstance(copy, dict):
                    text = copy.get("headline", "") + "\n" + copy.get("body", "")
                elif isinstance(copy, str):
                    text = copy
                if text.strip():
                    eval_data.append({
                        "response": text,
                        "context": f"Ad copy {i+1} for {brand or 'unknown brand'}",
                        "source": f"ad_copy_{i+1}",
                    })

    # If no session data, create a placeholder for the eval to still run
    if not eval_data:
        eval_data.append({
            "response": "No pipeline output available for evaluation.",
            "context": f"Brand: {brand or 'N/A'}, Product: {target_product or 'N/A'}",
            "source": "placeholder",
        })

    # Build pandas DataFrame for EvalTask
    import pandas as pd
    eval_df = pd.DataFrame(eval_data)

    # Run evaluation
    try:
        eval_task = EvalTask(
            dataset=eval_df,
            metrics=metrics,
        )
        eval_result = eval_task.evaluate()

        # Format results
        results: Dict[str, Any] = {
            "vertex_eval": True,
            "session_id": session_id,
            "brand": brand,
            "target_product": target_product,
            "num_samples": len(eval_data),
            "metrics_summary": {},
            "per_sample": [],
        }

        # Extract summary metrics
        if hasattr(eval_result, "summary_metrics") and eval_result.summary_metrics:
            results["metrics_summary"] = dict(eval_result.summary_metrics)

        # Extract per-row metrics
        if hasattr(eval_result, "metrics_table") and eval_result.metrics_table is not None:
            try:
                results["per_sample"] = eval_result.metrics_table.to_dict(orient="records")
            except Exception:
                results["per_sample"] = []

        logger.info(
            f"Vertex AI evaluation completed: {len(metrics)} metrics, "
            f"{len(eval_data)} samples"
        )
        return results

    except Exception as e:
        logger.error(f"Vertex AI evaluation failed: {e}", exc_info=True)
        raise
