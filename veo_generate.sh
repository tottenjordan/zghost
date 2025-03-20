#!/bin/bash

PROJECT_ID=wortz-project-352116
VEO_REQUEST_JSON_FILE=veo_request.json


curl -X POST \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -H "Content-Type: application/json; charset=utf-8" \
     -d @$VEO_REQUEST_JSON_FILE \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/$PROJECT_ID/locations/us-central1/publishers/google/models/veo-2.0-generate-001:predictLongRunning"