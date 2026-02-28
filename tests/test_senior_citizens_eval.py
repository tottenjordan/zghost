from google.adk.evaluation.agent_evaluator import AgentEvaluator

def test_senior_citizens_eval():
    AgentEvaluator.evaluate(
        agent_module="trends_and_insights_agent",
        eval_dataset_file_path_or_dir="tests/senior_citizens_eval.test.json",
    )
