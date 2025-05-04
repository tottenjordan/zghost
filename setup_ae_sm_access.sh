#!/bin/bash
# This is to run one-time to give Agent Engine access to the Youtube API Secret in Secret Manager

source trends_and_insights_agent/.env

export RE_SA="service-${GOOGLE_CLOUD_PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
gcloud secrets add-iam-policy-binding "projects/$GOOGLE_CLOUD_PROJECT_NUMBER/secrets/$YT_SECRET_MNGR_NAME" \
  --member="serviceAccount:$RE_SA" \
  --role="roles/secretmanager.secretAccessor"
