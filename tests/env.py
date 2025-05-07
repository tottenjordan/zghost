# Unit tests for env setup
import unittest
import os


class Env(unittest.TestCase):
    def test_env_vars(self):

        self.assertIsNot(os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER"), None)
        self.assertIsNot(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"), None)
        self.assertIsNot(os.environ.get("BUCKET"), None)
        self.assertIsNot(os.environ.get("GOOGLE_CLOUD_PROJECT"), None)
        self.assertIsNot(os.environ.get("YT_SECRET_MNGR_NAME"), None)
