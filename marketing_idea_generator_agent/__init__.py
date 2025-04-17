import os

os.environ["GOOGLE_CLOUD_PROJECT"] = "wortz-project-352116"
os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"] = "679926387543"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["BUCKET"] = "gs://zghost-media-center"

from . import agent

__all__ = ["agent"]