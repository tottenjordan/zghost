# Trend & Insight Agents

> *building multi-agent systems with Google's [Agent Development Kit](https://google.github.io/adk-docs/) (ADK)*

## Key Features
- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Ingest campaign brief outlining things like target audience, target regions, campaign objectives, product details, media strategy, etc.
- Perform targeted searches across Google Search and YouTube to gather initial inspiration, competitor insights, and relevant content
- Explore trends in Google Search and YouTube
- Brainstorm campaign concepts, taglines, messaging angles, etc.
- Draft ad creatives (e.g., image and video) based on campaign themes or specific prompts

# How to use this repo

## Setup

**TODO:** add instructions for enabling GCP APIs

Clone this repo and follow the steps below to create your virtual environment and install necessary packages:

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
  <summary>launching the ADK dev UI</summary>

```bash
adk web .
```

open the localhost to interact with your agents

</details>


## Deploying

```bash
adk deploy cloud_run --help
```

## YouTube Data API v3

<details>
  <summary>Create an API key</summary>

See [these instructions](https://developers.google.com/youtube/v3/getting-started) for getting a `YOUTUBE_DATA_API_KEY`

Store this API key in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets) as `yt-data-api`

</details>


*Example usage:*

1. REST API:

> `GET https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&regionCode=FR&key={YOUR_API_KEY}`

2. HTTP requests with `Python`

*config discovery client..*

```python
    youtube = googleapiclient.discovery.build(
        serviceName=API_SERVICE_NAME, 
        version=API_VERSION, 
        developerKey=YOUTUBE_DATA_API_KEY
    )
```

**Videos: list** - `Returns a list of videos that match the API request parameters`

```python
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode="US"
    )
    response = request.execute()
```

**Search: list** -`Returns a collection of search results that match the query parameters specified in the API request`

```python
    yt_data_api_request = youtube.search().list(
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