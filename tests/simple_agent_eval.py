from google.adk.evaluation.agent_evaluator import AgentEvaluator
# example of how to run this, using Pytest 
# Documentation links: https://google.github.io/adk-docs/evaluate/#2-pytest-run-tests-programmatically

def test_capability_query():
    AgentEvaluator.evaluate(
        agent_module="trends_and_insights_agent",
        eval_dataset_file_path_or_dir="tests/capability.test.json",
    )
