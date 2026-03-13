# Product fidelity evaluation using Gecko rubric-based scoring.
#
# Based on product-fidelity-eval by Bryan Eusebio:
#   https://github.com/behardja/product-fidelity-eval (branch: expand_video_feature)
#
# Gecko paper: "Gecko: Versatile Text Embeddings Distilled from Large Language Models"
#   https://arxiv.org/abs/2404.16820
#
# Vertex AI Evaluation Service (Gecko rubric metrics):
#   https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/evaluate-gen-ai
#   https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/metrics/rubric-based-metrics
from .gecko import evaluate
