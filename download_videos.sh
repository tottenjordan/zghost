#!bin/bash

BUCKET="gs://marketing-veo-output-jw-2025/march25"


gsutil cp -r $BUCKET/*/ video_output/