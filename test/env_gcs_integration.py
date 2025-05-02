import os
from dotenv import load_dotenv
import unittest

dotenv_path = os.path.join(
    os.path.dirname(__file__), "../trends_and_insights_agent/.env"
)
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # error:
    print("no .env file found")
    raise (FileNotFoundError, "no .env file found")


class Env(unittest.TestCase):
    def test_env_vars(self):

        self.assertIsNot(os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER"), None)
        self.assertIsNot(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"), None)
        self.assertIsNot(os.environ.get("BUCKET"), None)
        self.assertIsNot(os.environ.get("GOOGLE_CLOUD_PROJECT"), None)
        self.assertIsNot(os.environ.get("YT_SECRET_MNGR_NAME"), None)


BUCKET = os.environ.get("BUCKET")  # get this after validation


# set envs before package imports
from trends_and_insights_agent.common_agents.ad_content_generator.tools import (
    download_blob,
    upload_file_to_gcs,
)

test_file_name = "test_file.txt"
file_contents = "This is a test file for gcs integration."
with open(test_file_name, "w") as f:
    f.write(file_contents)

# convert the file to bytes
with open(test_file_name, "rb") as f:
    file_bytes = f.read()


class GCS(unittest.TestCase):
    def upload_file_to_gcs(self):
        # create a test file for upload to gcs

        # upload the test file to gcs
        upload_response = upload_file_to_gcs(
            file_path=test_file_name, file_data=file_bytes
        )

        self.assertEqual(upload_response, f"{BUCKET}/{test_file_name}")

    def download_blob(self):
        # download the test file from gcs
        download_response = download_blob(
            bucket_name=BUCKET.replace("gs://", ""), source_blob_name=test_file_name
        )
        self.assertEqual(download_response, file_contents.encode())


# delete the test file
os.remove(test_file_name)
