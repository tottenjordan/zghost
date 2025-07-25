# trends-2-creatives

> a multi-agent system finding the intersection between product, trend, and audience

<details>
  <summary>trends R us</summary>

<p align="center">
  <img src='media/deep-fried-trends.jpeg' width="700"/>
</p>

</details>

## About

*trends-2-creatives* is a marketing tool for developing data-driven and culturally relevant marketing strategies. Built with Google’s [Agent Development Kit (ADK)](https://google.github.io/adk-docs/), this multi-agent system helps users generate ad creatives from trending themes found in Google Search and YouTube.

- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Explore [trending Search terms](https://cloud.google.com/blog/products/data-analytics/top-25-google-search-terms-now-in-bigquery?e=48754805) and [trending YouTube videos](https://developers.google.com/youtube/v3/docs/videos/list)
- Conduct web research to better understand the campaign, Search trend, and trending YouTube video
- Draft ad creatives (e.g., image and video) based on trends, campaign themes, or specific prompts

<p align="center">
  <img src='media/t2a_overview_725.png' width="800"/>
</p>


## Example usage

<details>
  <summary>sample interaction</summary>

---

*In the ADK dev UI, follow these prompts to go from trends to creatives in ~5 mins*

**[entry point]** 

First we need **campaign metadata** e.g., `brand`, `target product`, `target audience`, `key selling points`, etc.

two options:
1. [Default] Agent will ask user for **campaign metadata** in the UI
2. [Optional] to preload these values, use the example json configs [shared_libraries/profiles/example_state_pixel.json](trends_and_insights_agent/shared_libraries/profiles/example_state_pixel.json) or upload your own. The json config you wish to reference should be set in your `.env` file like so:

```
SESSION_STATE_JSON_PATH=example_state_prs.json
```

*Note: remove or comment out this variable to use default option (1)*


```
> [user]: Hello...

> [agent]: Hello! I'm your AI Marketing Research & Strategy Assistant... To start, what please provide the following campaign metadata:

    * Brand
    * Target Product
    * Key Selling Points
    * Target Audience

> [user]: <provides campaign metadata>

> [agent]: [displays Search Trends]

> [user]: <selects interesting Search trend(s)>

> [agent]: [displays YouTube Trends]

> [user]: <selects interesting YouTube trend(s)>
```

**[campaign & trend research]** 

```
> [agent]: <executes pipeline of parallel research tasks>

> [agent]: [displays combined research report and saves as PDF artifact]
```


**[creative gen]** 

> Note: this section is configured for **human-in-the-loop** i.e., agent will iterate with user when generating image and video creatives

```
> [agent]: Now that I have all the research, I'll use the ad_content_generator_agent to help generate ad creatives based on the campaign themes, trend analysis, web research insights, and specific prompts.
```

1. Choose from a set of ad copies. Or create new ones from scratch
2. Edit suggested image prompts for the selected Ad Copy
3. Edit suggested video prompts for the generated image
4. Select attention-grabbing captions for the creatives

**[report gen]** 

```
> [agent]: Okay, we've gathered all the necessary research and generated the ad content. Now, I'll generate a comprehensive report outlining the campaign guide, search trends, YouTube trends, and insights from this session.
```

</details>


**sample ad creative**


<p align="center">
  <img src='media/t2a_hulk_call_Screen_v2.png' width="700"/>
</p>


# How to use this repo

1. Clone this repo (to local or Vertex AI Workbench Instance)
2. Open terminal, run commands under **One-time setup**
3. Create and store YouTube API key
4. Run commands under **Start a session**


## One-time setup

```bash
git clone https://github.com/tottenjordan/zghost.git
```

<details>
  <summary>Create & activate virtual environment</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
```

</details>


<details>
  <summary>Install packages</summary>

*install python packages...*

```bash
pip install pipx
pip install -U poetry packaging ipykernel

poetry install
```

</details>


<details>
  <summary>Authenticate and Enable Google Cloud APIs</summary>

```bash
gcloud auth application-default login

gcloud services enable artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    logging.googleapis.com \
    run.googleapis.com \
    storage-component.googleapis.com  \
    eventarc.googleapis.com \
    serviceusage.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    youtube.googleapis.com
```

</details>


<details>
  <summary>Create and store YouTube API key</summary>

1. See [these instructions](https://developers.google.com/youtube/v3/getting-started) for getting a `YOUTUBE_DATA_API_KEY`

2. Store this API key in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets) as `yt-data-api` (see `YT_SECRET_MNGR_NAME` in `.env` file)

   > For step-by-step guidance, see [create a secret and access a secret version](https://cloud.google.com/secret-manager/docs/create-secret-quickstart#create_a_secret_and_access_a_secret_version)

</details>


<details>
  <summary>Optionally, create notebook kernel</summary>

*create kernel with required packages for notebooks hosted in [Vertex AI Workbench Instances](https://cloud.google.com/vertex-ai/docs/workbench/instances/introduction)* 

*run this in instance terminal window:*

```bash
export ENV_NAME=py312_venv
DL_ANACONDA_ENV_HOME="${DL_ANACONDA_HOME}/envs/$ENV_NAME"
echo $DL_ANACONDA_ENV_HOME

python3 -m ipykernel install --prefix "${DL_ANACONDA_ENV_HOME}" --name $ENV_NAME --display-name $ENV_NAME
```

</details>


<details>
  <summary>Create and populate `.env` file(s)</summary>

*(1) create `.env` file for `root_agent`:*

```bash
touch .env
```

*(2) edit variables as needed:*

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=<YOUR_GCP_PROJECT_ID>
GOOGLE_CLOUD_PROJECT_NUMBER=<YOUR_GCP_PROJECT_NUMBER> # e.g., 1234756
GOOGLE_CLOUD_LOCATION=<YOUR_LOCATION> # e.g., us-central1
BUCKET=gs://<YOUR_GCS_BUCKET_NAME> # create a GCS bucket
YT_SECRET_MNGR_NAME=<YOUR_SECRET_NAME> # e.g., yt-data-api
SESSION_STATE_JSON_PATH=example_state_pixel.json
```

*(3) copy `.env` file to `root_agent` dir:*

```bash
cp .env trends_and_insights_agent/.env
cat trends_and_insights_agent/.env
```

*(4) read and execute `.env` file:*

```bash
source .env
```

</details>


<details>
  <summary>Create GCP assets and grant IAM</summary>

*create Cloud Storage bucket:*

```bash
gcloud storage buckets create $BUCKET --location=$GOOGLE_CLOUD_LOCATION
```

</details>


## Start a session

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
poetry run adk web
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
kill -9 $PID
lsof -i :8000
```

# Video walkthrough

> Updated version coming soon!


# Sub-agents & Tools

<p align="center">
  <img src='media/t2a_subagent_overview_0725.png' width="800"/>
</p>


<details>
  <summary>Staged Research Pipeline</summary>

<p align="center">
  <img src='media/t2a_staged_research_overview_2.png' width="800"/>
</p>

</details>


<details>
  <summary>Ad Content Generator Pipeline</summary>

<p align="center">
  <img src='media/t2a_ad_content_overview_2.png' width="800"/>
</p>

</details>


# CI And Testing

Using `pytest`, users can test for tool coverage as well as Agent evaluations.

More detail on agent evaluations [can be found here](https://google.github.io/adk-docs/evaluate/#2-pytest-run-tests-programmatically), along with how to run a `pytest` eval.

#### Running `pytest`

From the project root, run:

```bash
pytest tests/*.py
```

## Deployment

The agent can be deployed in a couple of different ways

1. Agent Engine
   * Here's an end-to-end guide on deploying
   * Be sure to first run the `setup_ae_sm_access.sh` script to give Agent Engine access to Secret Manager
   * Run the [deployment guide](.notebooks/deployment_guide.ipynb) to deploy the agent
2. Cloud Run
   * Run `deploy_to_cloud_run.sh`
   * Note this runs unit tests prior to deploying

Script for Cloud Run:

```bash
#!/bin/bash
source trends_and_insights_agent/.env

# run unit tests before deploying
pytest tests/*.py

# write requirements.txt to the agent folder
poetry export --without-hashes --format=requirements.txt >   trends_and_insights_agent/requirements.txt

#deploy to cloud run
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name='trends-and-insights-agent' \
  --with_ui \
  trends_and_insights_agent/
```

# Deployment to Agentspace


Create an Agent Engine in the `notebooks/deployment_guide.ipynb` notebook

Then note the Agent Engine ID (last numeric portion of the Resource Name). e.g.:

```bash
agent_engine = vertexai.agent_engines.get('projects/679926387543/locations/us-central1/reasoningEngines/1093257605637210112')
```

Update the `agent_config_example.json`, then run:

```bash
./publish_to_agentspace_v2.sh --action create --config agent_config.json
```

Usage: `./publish_to_agentspace_v2.sh [OPTIONS]`

```bash
Options:
  -a, --action <create|update|list|delete>  Action to perform (required)
  -c, --config <file>              JSON configuration file
  -p, --project-id <id>            Google Cloud project ID
  -n, --project-number <number>    Google Cloud project number
  -e, --app-id <id>                Agent Space application ID
  -r, --reasoning-engine <id>      Reasoning Engine ID (required for create/update)
  -d, --display-name <name>        Agent display name (required for create/update)
  -s, --description <desc>         Agent description (required for create)
  -i, --agent-id <id>              Agent ID (required for update/delete)
  -t, --instructions <text>        Agent instructions/tool description (required for create)
  -u, --icon-uri <uri>             Icon URI (optional)
  -l, --location <location>        Location (default: us)
  -h, --help                       Display this help message
```

### Example with config file:
```bash
./publish_to_agentspace_v2.sh --action create --config agent_config.json
./publish_to_agentspace_v2.sh --action update --config agent_config.json
./publish_to_agentspace_v2.sh --action list --config agent_config.json
./publish_to_agentspace_v2.sh --action delete --config agent_config.json
```
### Example with command line args:

Create agent:
```bash
./publish_to_agentspace_v2.sh --action create --project-id my-project --project-number 12345 \
--app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \
--description 'Agent description' --instructions 'Agent instructions here'
```
  Update agent:
```bash
./publish_to_agentspace_v2.sh --action update --project-id my-project --project-number 12345 \
--app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \
--agent-id 123456789 --description 'Updated description'
```
  List agents:
```bash
./publish_to_agentspace_v2.sh --action list --project-id my-project --project-number 12345 \
--app-id my-app
```

  Delete agent:
```bash
./publish_to_agentspace_v2.sh --action delete --project-id my-project --project-number 12345 \
--app-id my-app --agent-id 123456789
```