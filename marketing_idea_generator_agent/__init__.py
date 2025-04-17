import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "hybrid-vertex"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["BUCKET"] = "gs://zghost-media-center"

from . import agent

__all__ = ["agent"]