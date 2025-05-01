# Trend & Insight Agents

> *building multi-agent systems with Google's [Agent Development Kit](https://google.github.io/adk-docs/) (ADK)*

## About

Trends & Insights Agent is an advanced marketing tool built upon the foundation of Retail, CPG, and Google’s AI marketing tooling best practices. This version represents a significant leap forward, bringing enhanced capabilities with Google’s new [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)

**What Trends & Insights Can Do:**

-   **Streamline the Marketing Process:** From initial inspiration and competitive analysis to final creative drafts and reporting, TIA streamlines every step of the marketing workflow, making it easier to ideate, execute, and analyze campaigns, **significantly improving marketing use case velocity**.
-   **Leverage Advanced AI:** Utilizing cutting-edge LLM-based agents, Trends & Insights Agent empowers users to generate refined marketing briefs, draft ad creatives, and compile comprehensive report. These agents are powered by the diverse range of models available in Vertex AI's Model Garden.
-   **Deep Integration with Google Ecosystem:** Seamlessly gather real-time insights from Google Search trends, YouTube trends, using guardrails from your own internal campaign guidelines. This ensures marketing strategies are data-driven and culturally relevant.


**Rooted in Alphabet's/Google's Marketing Practices:**

-   **Act on Real-Time Insights:** Tap into the pulse of current trends and audience interests, ensuring that campaigns are always timely and relevant.
-   **Maintain Brand Consistency:** Ingest campaign guidelines to ensure all creative and messaging aligns with established brand voice and objectives.
-   **Optimize for Performance:** Leverage data-driven insights to refine strategies and maximize the impact of marketing efforts.

## Key Features

- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Ingest campaign guidelines outlining e.g., target audience, regions of interest, campaign objectives, product details, etc.
- Gather related content from Google Search and [YouTube](https://developers.google.com/youtube/v3/docs/search) for initial inspiration, competitor insights
- Explore trending Search terms and [trending YouTube videos](https://developers.google.com/youtube/v3/docs/videos/list)
- Generate refined marketing brief that includes e.g., campaign concepts, taglines, messaging angles, key insights, etc.
- Draft ad creatives (e.g., image and video) based on campaign themes or specific prompts
- Compile trends, insights, and campaign research into a comprehensive report


## Example usage

When interacting with the agent users can:
- Upload a PDF and get structured data outputs
- Query for general trends that are popular in various locations
- Broad research on new marketing ideas, leveraging web searching tools
- Generate new images based on insights from web searching or trend tool use

<video width="420" controls>
  <source src="https://github.com/tottenjordan/zghost/raw/refs/heads/main/TIA_trailer.mp4" type="video/mp4">
</video>

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

4. To start interacting with your agents, open the provided `localhost` link (e.g., `http://localhost:8000`) and select an agent from the drop-down (top left)

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

5. *Note: if port in use, find any processes listening to port `:8000`, kill them, then return to step (3):*

```bash
lsof -i :8000
kill -9 :8000
lsof -i :8000
```

### Deploying

```bash
adk deploy cloud_run --help
```

### Video walkthrough

> TODO: embed screencast demonstrating basic functionality and intended user journey

# Tools

> TODO: describe supported tools

## Google Search

> `googlesearch-python` is a Python library for searching Google

*References*
* [pypi project](https://pypi.org/project/googlesearch-python/)
* for `region` argument, see [country codes](https://developers.google.com/custom-search/docs/json_api_reference#countryCodes)
* see [this GitHub repo](https://github.com/Nv7-GitHub/googlesearch) for more examples

**Example usage**

1. *ability to search `terms` only or combine with the `site:` operator*

```python
from googlesearch import search
search_results_urls = []

# Google Search "widespread panic"
target_topic = "widespread panic"

# Google Search Reddit for content related to "widespread panic"
query = "site:reddit.com" + " " + target_topic

lang = "en"
region = "us"
pause_time = 2.0
num_results = 10

results_generator = search(
    term=query, # query | target_topic
    lang=lang,
    region=region,
    num_results=num_results, 
    sleep_interval=pause_time,
    unique=True,
    advanced=False, # returns list of URLs
)

search_results_urls = list(results_generator)
search_results_urls[0]
```
*returns URL string:*

```python
'https://www.reddit.com/r/WidespreadPanic/'
```

2. *Setting `advanced=True` returns list of `SearchResult` objects (title, url, description)*

```python
results_generator = search(
    term=query,
    lang=lang,
    region=region,
    num_results=num_results, 
    sleep_interval=pause_time,
    unique=True,
    advanced=True, # returns list of SearchResult
)
search_results = list(results_generator)
search_results[0]
```
*returns `SearchResult` object:*

```python
SearchResult(
  url="https://www.reddit.com/r/jambands/comments/1e6hjl9/widespread_panic_appreciation_thread/", 
  title="Widespread Panic Appreciation Thread : r/jambands - Reddit",
  description="Jul 18,2024·In a jam band world of the goofy, wookie, entitled and sometimes creepy-ass fans, panic's fans remain undefeated..."
)
```


## Google News

> `GoogleNews` is a Python library for searching [Google News](https://news.google.com/)

*References*
* [pypi project](https://pypi.org/project/GoogleNews/)

**Example usage**

1. *Can only search `terms`; **cannot combine** with the `site:` operator*

```python
from GoogleNews import GoogleNews
googlenews = GoogleNews()

# initialize 
googlenews = GoogleNews(
    lang='en', 
    region='US',
    # period='7d',
    # start='02/01/2020',
    # end='02/28/2020',
    # encode='utf-8',
)

# enable throw exception
googlenews.enableException(True)

# can only search terms
query = "widespread panic"

# set topic/query for news
news_wsp = googlenews.get_news(query)

# get the news results dictionary
news_wsp_results = googlenews.results(sort=True) # order the results in cronologically reversed order

# get URLs only
news_wsp_links = googlenews.get_links()

# get article titles only
news_wsp_titles = googlenews.get_texts()

# clear result list before doing another search with the same object
googlenews.clear()
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
