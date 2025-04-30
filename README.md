# Trend & Insight Agents

> *building multi-agent systems with Google's [Agent Development Kit](https://google.github.io/adk-docs/) (ADK)*

## Key Features

- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Ingest campaign guidelines outlining e.g., target audience, regions of interest, campaign objectives, product details, etc.
- Gather related content from Google Search and [YouTube](https://developers.google.com/youtube/v3/docs/search) for initial inspiration, competitor insights
- Explore trending Search terms and [trending YouTube videos](https://developers.google.com/youtube/v3/docs/videos/list)
- Generate refined marketing brief that includes e.g., campaign concepts, taglines, messaging angles, key insights, etc.
- Draft ad creatives (e.g., image and video) based on campaign themes or specific prompts
- Compile trends, insights, and campaign research into a comprehensive report

## How to use this repo

1. Clone this repo (to local or Vertex AI Workbench Instance)
2. Open a terminal and run below commands

### One-time setup

```bash
git clone https://github.com/tottenjordan/zghost.git
```

<details>
  <summary>Create & activate virtual environment</summary>

```bash
sudo apt-get install virtualenv python3-venv python3-pip

python3 -m venv .venv

source .venv/bin/activate
```

</details>


<details>
  <summary>Install packages</summary>

*Optionally install `ipykernel` to run/test in notebooks*

```bash
pip install pipx
pip install -U poetry packaging ipykernel

poetry install

poetry env use 3.12
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


<details>
  <summary>Optionally, create notebook kernels</summary>

*create kernel with required packages for notebooks hosted locally or in [Vertex AI Workbench Instances](https://cloud.google.com/vertex-ai/docs/workbench/instances/introduction)* 

**Notebook hosted locally**

```bash
export ENV_NAME=py312_venv
python3 -m ipykernel install --user --name $ENV_NAME --display-name $ENV_NAME
```

**Notebook hosted in Vertex AI Workbench**

*run this in instance terminal window:*

```bash
export ENV_NAME=py312_venv
DL_ANACONDA_ENV_HOME="${DL_ANACONDA_HOME}/envs/$ENV_NAME"
echo $DL_ANACONDA_ENV_HOME

python3 -m ipykernel install --prefix "${DL_ANACONDA_ENV_HOME}" --name $ENV_NAME --display-name $ENV_NAME
```

*In either option, open a notebook file and select your kernel (top right). Should see `$ENV_NAME` as an available kernel* 

</details>


<details>
  <summary>Create and populate `.env` file(s)</summary>

*create `.env` file for `root_agent`:*

```bash
touch .env
nano .env
```

*edit variables as needed:*

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=YOUR_GCP_PROJECT_ID
GOOGLE_CLOUD_PROJECT_NUMBER=YOUR_GCP_PROJECT_NUMBER # e.g., 1234756
GOOGLE_CLOUD_LOCATION=YOUR_LOCATION # e.g., us-central1
YT_SECRET_MNGR_NAME=YOUR_SECRET_NAME # e.g., yt-data-api
GOOGLE_API_KEY=None # Optional
BUCKET=gs://YOUR_GCS_BUCKET_NAME # create a GCS bucket
```

*copy `.env` file to `root_agent` dir:*

```bash
cp .env marketing_idea_generator_agent/.env
cat marketing_idea_generator_agent/.env
```

*read and execute `.env` file:*

```bash
source .env
```

</details>


<details>
  <summary>Create GCP assets and grant IAM</summary>

*create Cloud Storage bucket:*

```bash
gcloud storage buckets create gs://$BUCKET --location=$GOOGLE_CLOUD_LOCATION
```

**TODOs:**
* create BigQuery tables for Trends dataset
* create commands for granting proper IAM to each asset

</details>


### Running locally

When starting a new session (e.g., after a new code commit, package update/add, etc.):

1. activate the `virtual environment` 
2. `source` the `.env` file 

```bash
source .venv/bin/activate`

source .env
echo $BUCKET
```

3. launch the adk developer UI

```bash
adk web .
```

4. To start interacting with your agents, open the provided `localhost` link (e.g., `http://0.0.0.0:8000`)

```bash
INFO:     Started server process [750453]
INFO:     Waiting for application startup.

+-----------------------------------------------------------------------------+
| ADK Web Server started                                                      |
|                                                                             |
| For local testing, access at http://localhost:8000.                         |
+-----------------------------------------------------------------------------+

INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

5. *Note: if port in use, find any processes listening to port `:8000`, kill them, then return to step (3):

```bash
lsof -i :8000
kill -9 :8000
lsof -i :8000
```


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