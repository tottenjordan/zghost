# Unit tests for env setup
import unittest
import os

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
