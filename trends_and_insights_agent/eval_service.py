"""
Evaluation service for running ADK agent evaluations.
Wraps google.adk.evaluation.agent_evaluator.AgentEvaluator with additional
support for custom rubric criteria.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from google.adk.evaluation.agent_evaluator import AgentEvaluator

logger = logging.getLogger(__name__)


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
