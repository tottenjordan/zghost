"""
Evaluation Pipeline for Trends & Insights Agent

Runs a 2-epoch evaluation with:
- Granular artifacts per run (JSON reports per epoch/case)
- Run descriptions with lineage tracking (epoch -> eval_case -> invocation)
- Rubric-based metrics with detailed scoring breakdown

Usage:
    uv run pytest tests/eval_pipeline.py -v
    uv run pytest tests/eval_pipeline.py -v -s  # with stdout
"""

import asyncio
import json
import logging
import os
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pytest

from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.eval_case import EvalCase, Invocation, get_all_tool_calls
from google.adk.evaluation.eval_config import EvalConfig, get_eval_metrics_from_config
from google.adk.evaluation.eval_metrics import (
    EvalMetric,
    EvalMetricResult,
    EvalMetricResultPerInvocation,
    PrebuiltMetrics,
)
from google.adk.evaluation.eval_result import EvalCaseResult, EvalSetResult
from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.evaluator import EvalStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NUM_EPOCHS = 2
AGENT_MODULE = "trends_and_insights_agent"
EVAL_CASES_FILE = "tests/eval_cases.test.json"
EVAL_CONFIG_FILE = "tests/test_config.json"
ARTIFACTS_DIR = Path("tests/eval_artifacts")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_eval_set(eval_cases_file: str) -> EvalSet:
    with open(eval_cases_file, "r", encoding="utf-8") as f:
        return EvalSet.model_validate_json(f.read())


def load_eval_config(config_file: str) -> EvalConfig:
    with open(config_file, "r", encoding="utf-8") as f:
        return EvalConfig.model_validate_json(f.read())


def build_run_descriptor(
    epoch: int,
    eval_case_id: str,
    eval_set_id: str,
    run_id: str,
    parent_run_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a lineage descriptor for a single run."""
    return {
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "epoch": epoch,
        "eval_set_id": eval_set_id,
        "eval_case_id": eval_case_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lineage": f"epoch_{epoch} -> {eval_set_id} -> {eval_case_id}",
        "description": (
            f"Epoch {epoch} evaluation of case '{eval_case_id}' "
            f"from eval set '{eval_set_id}'"
        ),
    }


def extract_rubric_metrics(
    eval_case_result: EvalCaseResult,
) -> list[dict[str, Any]]:
    """Extract granular rubric-level metrics from an EvalCaseResult."""
    rubric_metrics = []
    for per_inv in eval_case_result.eval_metric_result_per_invocation:
        for metric_result in per_inv.eval_metric_results:
            entry = {
                "metric_name": metric_result.metric_name,
                "score": metric_result.score,
                "threshold": metric_result.threshold,
                "eval_status": metric_result.eval_status.name,
            }
            if metric_result.details and metric_result.details.rubric_scores:
                entry["rubric_scores"] = [
                    {
                        "rubric_id": rs.rubric_id,
                        "score": rs.score,
                        "rationale": rs.rationale,
                    }
                    for rs in metric_result.details.rubric_scores
                ]
            rubric_metrics.append(entry)
    return rubric_metrics


def extract_overall_metrics(
    eval_case_result: EvalCaseResult,
) -> list[dict[str, Any]]:
    """Extract overall metric summaries."""
    return [
        {
            "metric_name": m.metric_name,
            "score": m.score,
            "threshold": m.threshold,
            "eval_status": m.eval_status.name,
        }
        for m in eval_case_result.overall_eval_metric_results
    ]


def build_run_artifact(
    run_descriptor: dict[str, Any],
    eval_case_result: EvalCaseResult,
) -> dict[str, Any]:
    """Build a granular artifact for a single run."""
    return {
        "run_descriptor": run_descriptor,
        "overall_status": eval_case_result.final_eval_status.name,
        "session_id": eval_case_result.session_id,
        "overall_metrics": extract_overall_metrics(eval_case_result),
        "granular_metrics": extract_rubric_metrics(eval_case_result),
        "invocation_count": len(
            eval_case_result.eval_metric_result_per_invocation
        ),
    }


def save_artifact(artifact: dict[str, Any], filepath: Path) -> None:
    """Persist a run artifact as JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, default=str)
    logger.info(f"Saved artifact: {filepath}")


def build_epoch_summary(
    epoch: int,
    epoch_id: str,
    run_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an epoch-level summary aggregating all runs."""
    all_scores = []
    metric_scores: dict[str, list[float]] = {}

    for art in run_artifacts:
        for m in art["granular_metrics"]:
            if m["score"] is not None:
                all_scores.append(m["score"])
                metric_scores.setdefault(m["metric_name"], []).append(m["score"])

    return {
        "epoch": epoch,
        "epoch_id": epoch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_runs": len(run_artifacts),
        "aggregate_score": statistics.mean(all_scores) if all_scores else None,
        "per_metric_averages": {
            name: statistics.mean(scores) for name, scores in metric_scores.items()
        },
        "run_statuses": {
            art["run_descriptor"]["eval_case_id"]: art["overall_status"]
            for art in run_artifacts
        },
        "runs": [art["run_descriptor"] for art in run_artifacts],
    }


# ---------------------------------------------------------------------------
# Core evaluation runner
# ---------------------------------------------------------------------------

async def run_eval_epoch(
    epoch: int,
    agent_module: str,
    eval_set: EvalSet,
    eval_config: EvalConfig,
    parent_epoch_id: Optional[str] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run a single epoch of evaluation and return (epoch_id, run_artifacts)."""
    epoch_id = f"epoch_{epoch}_{uuid.uuid4().hex[:8]}"
    eval_metrics = get_eval_metrics_from_config(eval_config)

    agent_for_eval = await AgentEvaluator._get_agent_for_eval(
        module_name=agent_module
    )

    from google.adk.evaluation.simulation.user_simulator_provider import (
        UserSimulatorProvider,
    )

    user_sim_provider = UserSimulatorProvider(
        user_simulator_config=eval_config.user_simulator_config
    )

    eval_results_by_id = await AgentEvaluator._get_eval_results_by_eval_id(
        agent_for_eval=agent_for_eval,
        eval_set=eval_set,
        eval_metrics=eval_metrics,
        num_runs=1,  # 1 run per epoch; we control epochs externally
        user_simulator_provider=user_sim_provider,
    )

    run_artifacts = []
    for eval_case_id, case_results in eval_results_by_id.items():
        for case_result in case_results:
            run_id = f"{epoch_id}_{eval_case_id}_{uuid.uuid4().hex[:6]}"
            descriptor = build_run_descriptor(
                epoch=epoch,
                eval_case_id=eval_case_id,
                eval_set_id=eval_set.eval_set_id,
                run_id=run_id,
                parent_run_id=parent_epoch_id,
            )
            artifact = build_run_artifact(descriptor, case_result)
            run_artifacts.append(artifact)

            # Save granular per-run artifact
            artifact_path = (
                ARTIFACTS_DIR / f"epoch_{epoch}" / f"{eval_case_id}.json"
            )
            save_artifact(artifact, artifact_path)

    return epoch_id, run_artifacts


async def run_full_evaluation(
    num_epochs: int = NUM_EPOCHS,
) -> dict[str, Any]:
    """Run the full multi-epoch evaluation pipeline."""
    eval_set = load_eval_set(EVAL_CASES_FILE)
    eval_config = load_eval_config(EVAL_CONFIG_FILE)

    pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
    epoch_summaries = []
    all_artifacts = []
    parent_epoch_id = None

    for epoch in range(1, num_epochs + 1):
        logger.info(f"--- Starting Epoch {epoch}/{num_epochs} ---")
        start_time = time.time()

        epoch_id, run_artifacts = await run_eval_epoch(
            epoch=epoch,
            agent_module=AGENT_MODULE,
            eval_set=eval_set,
            eval_config=eval_config,
            parent_epoch_id=parent_epoch_id,
        )

        elapsed = time.time() - start_time
        summary = build_epoch_summary(epoch, epoch_id, run_artifacts)
        summary["elapsed_seconds"] = round(elapsed, 2)
        epoch_summaries.append(summary)
        all_artifacts.extend(run_artifacts)

        # Chain lineage: next epoch's parent is this epoch
        parent_epoch_id = epoch_id

        # Save epoch summary
        save_artifact(
            summary, ARTIFACTS_DIR / f"epoch_{epoch}" / "epoch_summary.json"
        )

    # Build final pipeline report
    pipeline_report = {
        "pipeline_id": pipeline_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_epochs": num_epochs,
        "eval_set_id": eval_set.eval_set_id,
        "eval_set_description": eval_set.description,
        "epoch_summaries": epoch_summaries,
        "lineage_chain": [s["epoch_id"] for s in epoch_summaries],
        "total_runs": len(all_artifacts),
        "rubric_catalog": _extract_rubric_catalog(eval_config),
    }

    save_artifact(pipeline_report, ARTIFACTS_DIR / "pipeline_report.json")
    return pipeline_report


def _extract_rubric_catalog(eval_config: EvalConfig) -> list[dict[str, Any]]:
    """Extract the rubric catalog from the eval config for documentation."""
    catalog = []
    for metric_name, criterion in eval_config.criteria.items():
        entry = {"metric_name": metric_name}
        # Normalize criterion to a dict
        if isinstance(criterion, (int, float)):
            entry["threshold"] = criterion
            catalog.append(entry)
            continue
        crit_dict = (
            criterion if isinstance(criterion, dict)
            else criterion.model_dump() if hasattr(criterion, "model_dump")
            else vars(criterion)
        )
        entry["threshold"] = crit_dict.get("threshold")
        rubrics_raw = crit_dict.get("rubrics", [])
        if rubrics_raw:
            entry["rubrics"] = []
            for r in rubrics_raw:
                rd = r if isinstance(r, dict) else (r.model_dump() if hasattr(r, "model_dump") else vars(r))
                rc = rd.get("rubric_content", rd.get("rubricContent", {}))
                if isinstance(rc, dict):
                    tp = rc.get("text_property", rc.get("textProperty"))
                else:
                    tp = getattr(rc, "text_property", None)
                entry["rubrics"].append({
                    "rubric_id": rd.get("rubric_id", rd.get("rubricId")),
                    "description": rd.get("description"),
                    "type": rd.get("type"),
                    "text_property": tp,
                })
        catalog.append(entry)
    return catalog


# ---------------------------------------------------------------------------
# Pytest entry points
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_report():
    """Run the full 2-epoch evaluation pipeline."""
    return asyncio.run(run_full_evaluation(num_epochs=NUM_EPOCHS))


def test_pipeline_completes(pipeline_report):
    """The pipeline runs 2 epochs and produces a report."""
    assert pipeline_report["num_epochs"] == NUM_EPOCHS
    assert len(pipeline_report["epoch_summaries"]) == NUM_EPOCHS
    assert pipeline_report["total_runs"] > 0
    print(f"\nPipeline {pipeline_report['pipeline_id']} completed:")
    print(f"  Epochs: {pipeline_report['num_epochs']}")
    print(f"  Total runs: {pipeline_report['total_runs']}")


def test_granular_artifacts_exist(pipeline_report):
    """Each run produces a granular artifact file."""
    for epoch_summary in pipeline_report["epoch_summaries"]:
        epoch = epoch_summary["epoch"]
        epoch_dir = ARTIFACTS_DIR / f"epoch_{epoch}"
        assert epoch_dir.exists(), f"Missing artifact dir for epoch {epoch}"

        summary_file = epoch_dir / "epoch_summary.json"
        assert summary_file.exists(), f"Missing epoch summary for epoch {epoch}"

        # Verify at least one run artifact per epoch
        run_files = [f for f in epoch_dir.iterdir() if f.name != "epoch_summary.json"]
        assert len(run_files) > 0, f"No run artifacts in epoch {epoch}"
        print(f"\n  Epoch {epoch}: {len(run_files)} run artifact(s)")


def test_run_lineage_tracking(pipeline_report):
    """Each run has a descriptor with lineage back to its epoch."""
    lineage_chain = pipeline_report["lineage_chain"]
    assert len(lineage_chain) == NUM_EPOCHS

    for i, epoch_summary in enumerate(pipeline_report["epoch_summaries"]):
        for run in epoch_summary["runs"]:
            assert "lineage" in run, f"Missing lineage in run {run['run_id']}"
            assert "epoch" in run["lineage"]
            assert run["eval_set_id"] == pipeline_report["eval_set_id"]

            # Verify parent chaining (epoch 2's parent = epoch 1's id)
            if i > 0:
                expected_parent = lineage_chain[i - 1]
                assert run["parent_run_id"] == expected_parent, (
                    f"Run {run['run_id']} parent should be {expected_parent}, "
                    f"got {run['parent_run_id']}"
                )
            print(f"\n  {run['description']}")


def test_rubric_catalog_documented(pipeline_report):
    """The rubric catalog is present and describes each metric."""
    catalog = pipeline_report["rubric_catalog"]
    assert len(catalog) > 0, "Rubric catalog is empty"

    rubric_metrics = [c for c in catalog if "rubrics" in c]
    assert len(rubric_metrics) > 0, "No rubric-based metrics in catalog"

    for entry in catalog:
        assert "metric_name" in entry
        assert "threshold" in entry
        print(f"\n  Metric: {entry['metric_name']} (threshold={entry['threshold']})")
        if "rubrics" in entry:
            for r in entry["rubrics"]:
                print(f"    Rubric: {r['rubric_id']} [{r['type']}]")
                print(f"      {r['description']}")


def test_granular_metrics_per_run(pipeline_report):
    """Each epoch has per-run granular metrics with scores."""
    for epoch_summary in pipeline_report["epoch_summaries"]:
        epoch = epoch_summary["epoch"]
        assert "per_metric_averages" in epoch_summary
        assert "aggregate_score" in epoch_summary

        print(f"\n  Epoch {epoch}:")
        print(f"    Aggregate score: {epoch_summary['aggregate_score']}")
        for metric, avg in epoch_summary["per_metric_averages"].items():
            print(f"    {metric}: {avg:.3f}")


def test_epoch_to_epoch_comparison(pipeline_report):
    """Both epochs ran and we can compare scores across them."""
    summaries = pipeline_report["epoch_summaries"]
    assert len(summaries) == 2

    e1 = summaries[0]
    e2 = summaries[1]
    print(f"\n  Epoch 1 aggregate: {e1['aggregate_score']}")
    print(f"  Epoch 2 aggregate: {e2['aggregate_score']}")
    print(f"  Epoch 1 elapsed: {e1.get('elapsed_seconds', 'N/A')}s")
    print(f"  Epoch 2 elapsed: {e2.get('elapsed_seconds', 'N/A')}s")

    # Both epochs should have results (we don't assert equal scores, just that both ran)
    assert e1["total_runs"] > 0
    assert e2["total_runs"] > 0
