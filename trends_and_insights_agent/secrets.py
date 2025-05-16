import os
import google_crc32c
from google.cloud import secretmanager as sm

# Get the project ID from the environment variable
try:
    project_number = os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"]
except KeyError:
    raise Exception("GOOGLE_CLOUD_PROJECT_NUMBER environment variable not set")


# [START secretmanager_get_secret_version]


def access_secret_version(
    secret_id: str, version_id: str
) -> sm.AccessSecretVersionResponse:
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """

    # Create the Secret Manager client.
    sm_client = sm.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_number}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = sm_client.access_secret_version(request={"name": name})

    # Verify payload checksum.
    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        print("Data corruption detected.")
        return response

    # Print the secret payload.
    #
    # WARNING: Do not print the secret in a production environment - this
    # snippet is showing how to access the secret material.
    payload = response.payload.data.decode("UTF-8")
    return payload
