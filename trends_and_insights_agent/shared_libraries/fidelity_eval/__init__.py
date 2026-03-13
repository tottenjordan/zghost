"""Product fidelity evaluation using Gecko rubric-based scoring.

Based on Gecko: Versatile Text Embeddings Distilled from Large Language Models
    Jinhyuk Lee, Zhuyun Dai, Xiaoqi Ren, et al. (2024)
    https://arxiv.org/abs/2404.16820

Adapted from: https://github.com/behardja/product-fidelity-eval
    (branch: expand_video_feature) by Bryan Eusebio

Vertex AI Evaluation Service (Gecko rubric metrics):
    https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/evaluate-gen-ai
    https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/metrics/rubric-based-metrics
"""
from .gecko import evaluate
