PROJECT_ID=veo-testing
OPERATION_ID="dfe9914b-b995-4766-853e-73421b19668d"

cat > request.json <<EOF
{"operationName": "projects/${PROJECT_ID}/locations/us-central1/publishers/google/models/veo-2.0-generate-001/operations/${OPERATION_ID}"}
EOF


curl -X POST \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -H "Content-Type: application/json; charset=utf-8" \
     -d @request.json \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/$PROJECT_ID/locations/us-central1/publishers/google/models/veo-2.0-generate-001:fetchPredictOperation"