# Trend & Insight Agents

> *building multi-agent systems with Google's [Agent Development Kit](https://google.github.io/adk-docs/) (ADK)*

## Key Features
- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Ingest campaign brief outlining things like target audience, regions, campaign objectives, product details, etc.
- Perform targeted searches across Google Search and YouTube to gather inspiration, competitor insights, and related content
- Explore trends in Google Search and YouTube (e.g, Shorts)
- Brainstorm campaign concepts, taglines, messaging angles, etc.
- Draft ad creatives (e.g., image and video) based on campaign themes or specific prompts
- Compile trends, insights, and campaign research into a comprehensive report

## How to use this repo

Clone this repo and follow the steps below to get started

### Setup

<details>
  <summary>Create & activate virtual environment</summary>

```bash
sudo apt-get install virtualenv python3-venv python3-pip

python3 -m venv .venv

source .venv/bin/activate
```
</details>

<details>
  <summary>Install packages and create kernel to run notebooks</summary>

```bash
pip install pipx
pip install -U poetry ipykernel packaging

export ENV_NAME=py312_venv
python3 -m ipykernel install --user --name $ENV_NAME --display-name $ENV_NAME

poetry install

poetry env use 3.12
```
</details>

<details>
  <summary>Create and populate an `.env` file</summary>

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=YOUR_GCP_PROJECT_ID
GOOGLE_CLOUD_PROJECT_NUMBER=YOUR_GCP_PROJECT_NUMBER
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_API_KEY=None
BUCKET=gs://YOUR_GCS_BUCKET_NAME
```
</details>


<details>
  <summary>Enable Google cloud APIs</summary>

```bash
gcloud services enable artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    logging.googleapis.com \
    run.googleapis.com \
    storage-component.googleapis.com  \
    eventarc.googleapis.com \
    serviceusage.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com
```
</details>

### Running locally

After completing the one-time setup instructions, run the below command to launch the ADK's interactive dev UI:

```bash
adk web .
```
open the localhost to interact with your agents


### Deploying

```bash
adk deploy cloud_run --help
```

## YouTube Data API v3

<details>
  <summary>Create and store API key</summary>

1. See [these instructions](https://developers.google.com/youtube/v3/getting-started) for getting a `YOUTUBE_DATA_API_KEY`

2. Store this API key in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets) as `yt-data-api`. See [create a secret and access a secret version](https://cloud.google.com/secret-manager/docs/create-secret-quickstart#create_a_secret_and_access_a_secret_version) or step-by-step guidance

</details>

**Example usage**

REST API:

> `GET https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&regionCode=FR&key={YOUR_API_KEY}`

HTTP requests with `Python`

*config discovery client..*

```python
import googleapiclient.discovery

youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", 
    version="v3", 
    developerKey=YOUTUBE_DATA_API_KEY
)
```

**Videos: list** - `Returns a list of videos that match the API request parameters`

```python
    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode="US"
    )
    response = request.execute()
```

**Search: list** -`Returns a collection of search results that match the query parameters specified in the API request`

```python
    yt_data_api_request = youtube_client.search().list(
        part="id,snippet",
        type="video",
        q=TARGET_QUERY,
        videoDuration=VIDEO_DURATION,
        maxResults=NUM_RESULTS,
        publishedAfter=PUBLISHED_AFTER_TIMESTAMP,
        channelId=CHANNEL_ID,
        order=ORDER_CRITERIA,
    )
    yt_data_api_response = yt_data_api_request.execute()
```
 
</details>