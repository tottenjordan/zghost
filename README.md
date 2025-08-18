# trends-2-creatives

> a multi-agent system finding the intersection between product, trend, and audience

<details>
  <summary>trends R us</summary>

<p align="center">
  <img src='media/deep-fried-trends.jpeg' width="700"/>
</p>

</details>

## About

*trends-2-creatives* is a marketing tool for developing data-driven and culturally relevant marketing content. Built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/), this multi-agent system helps users generate ad creatives from trending themes in Google Search and YouTube.

- Build LLM-based agents with [models supported in Vertex AI's Model Garden](https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/available-models)
- Explore [trending Search terms](https://cloud.google.com/blog/products/data-analytics/top-25-google-search-terms-now-in-bigquery?e=48754805) and [trending YouTube videos](https://developers.google.com/youtube/v3/docs/videos/list)
- Conduct web research to better understand the campaign, Search trend, and trending YouTube video
- Draft ad creatives (e.g., image and video) based on trends, campaign themes, or specific prompts
- **NEW**: Supports the [a2a protocol](https://a2a-protocol.org/) for modular, distributed agent deployment
- **NEW**: Unified a2a server architecture that enables scalable agent interactions

<p align="center">
  <img src='media/t2a_overview_0725_v2.png' width="800"/>
</p>

## How to use this repo

1. **Clone the repository**

```bash
git clone https://github.com/tottenjordan/zghost.git
```

2. **Create a virtual environment and install dependencies**

```bash
python3 -m venv .venv && source .venv/bin/activate

pip install pipx
pip install -U poetry packaging ipykernel

poetry install
```

3. **Authenticate and Enable Google Cloud APIs**

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

4. **Create and store YouTube API key**

  - See [these instructions](https://developers.google.com/youtube/v3/getting-started) for getting a `YOUTUBE_DATA_API_KEY`
  - Store this API key in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets) as `yt-data-api` (see `YT_SECRET_MNGR_NAME` in `.env` file)
     - For step-by-step guidance, see [create a secret and access a secret version](https://cloud.google.com/secret-manager/docs/create-secret-quickstart#create_a_secret_and_access_a_secret_version)


5. **Create and populate `.env` file(s)**

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=<YOUR_GCP_PROJECT_ID>
GOOGLE_CLOUD_PROJECT_NUMBER=<YOUR_GCP_PROJECT_NUMBER> # e.g., 1234756
GOOGLE_CLOUD_LOCATION=<YOUR_LOCATION> # e.g., us-central1
BUCKET=gs://<YOUR_GCS_BUCKET_NAME> # create a GCS bucket
YT_SECRET_MNGR_NAME=<YOUR_SECRET_NAME> # e.g., yt-data-api
# SESSION_STATE_JSON_PATH=example_state_pixel.json # uncomment to use default config values
```

*copy `.env` file to `root_agent` dir:*

```bash
cp .env trends_and_insights_agent/.env
cat trends_and_insights_agent/.env

source .env
```

 6. **Create Cloud Storage bucket**

```bash
gcloud storage buckets create $BUCKET --location=$GOOGLE_CLOUD_LOCATION
```

7. **Launch the application**

The application now includes a modern React frontend and supports the **a2a (agent-to-agent) protocol** for modular, distributed agent deployment.

### Quick Start - ADK Web UI with A2A (Recommended)

```bash
make install  # First time only

# Terminal 1: Start A2A server
make a2a-servers

# Terminal 2: Start ADK web UI
make orchestrator-consumer
```
Then open [http://localhost:8000](http://localhost:8000) in your browser to use the ADK web interface.

### Alternative: React Frontend with A2A

```bash
make a2a-dev  # Starts all services
```
Then open [http://localhost:5173](http://localhost:5173) for the React interface.

### Detailed Options

### Option 1: ADK Web Interface with A2A Architecture (recommended)

```bash
# Terminal 1 - Start A2A server
make a2a-servers

# Terminal 2 - Start orchestrator consumer with ADK web UI
make orchestrator-consumer
```

This starts:
- A2A server on [http://localhost:8100](http://localhost:8100)
- ADK Web UI on [http://localhost:8000](http://localhost:8000)

### Option 2: React Frontend with A2A Architecture

```bash
# Run all services with a2a architecture
make a2a-dev
```

This single command starts everything:
- A2A server on [http://localhost:8100](http://localhost:8100)
- Backend API server on [http://localhost:8000](http://localhost:8000)
- Artifact server on [http://localhost:8001](http://localhost:8001)
- Frontend React app on [http://localhost:5173](http://localhost:5173)

### Option 3: Classic architecture (without A2A)

```bash
# Install dependencies and run traditional architecture
make install
make dev
```

This uses the monolithic architecture with all agents in-process.

### Option 4: Run services separately

**For A2A Architecture:**
```bash
# Terminal 1 - A2A Server
make a2a-servers

# Terminal 2 - Orchestrator Consumer (ADK Web)
make orchestrator-consumer
```

**For Classic Architecture:**
```bash
# Terminal 1 - Backend
make backend

# Terminal 2 - Artifact Server
make artifact-server

# Terminal 3 - Frontend (optional)
make frontend
```

### Option 5: Classic ADK CLI interface

```bash
poetry run adk run trends_and_insights_agent
```

<details>
  <summary>If port :8000, :8001, :5173, or :8100 is in use</summary>

*find any processes listening to these ports, kill them, then restart:*

```bash
# For backend port
lsof -i :8000
kill -9 $PID

# For artifact server port
lsof -i :8001
kill -9 $PID

# For frontend port
lsof -i :5173
kill -9 $PID

# For a2a server port
lsof -i :9000
kill -9 $PID
```

</details>

## A2A Protocol Architecture

The application now supports the **a2a (agent-to-agent) protocol**, enabling modular and distributed deployment of agents. This architecture provides:

### Benefits of A2A Architecture

- **Modularity**: Each agent runs as an independent service with its own API
- **Scalability**: Agents can be scaled independently based on demand
- **Flexibility**: Mix and match agents, replace implementations without affecting others
- **Distributed Deployment**: Run agents on different machines or cloud services
- **Language Agnostic**: Agents can be implemented in any language that supports HTTP

### A2A Orchestrator Service

The system includes a single a2a orchestrator server (port 9000) that manages all agent interactions:

**Orchestrator Components:**
- **Trends & Insights**: Handles trend selection, PDF extraction, and YouTube summaries
- **Research Orchestrator**: Coordinates parallel research and synthesizes reports
- **Ad Generator**: Creates ad copy, visual concepts, and generates media with Imagen/Veo

### Integration Patterns

The refactored architecture supports three integration patterns:

- **A2A Server Architecture**: Agents run as separate HTTP services (recommended for production)
- **Direct Sub-Agent Integration**: Agents run in-process as sub-agents (simpler deployment)
- **Classic Monolithic**: Original single-process architecture (simplest setup)

## Frontend Features

The React frontend provides an enhanced user experience for interacting with the marketing intelligence agents:

### Key Features
- **Interactive Welcome Screen**: Quick start guide and example queries to get you started
- **Real-time Agent Visualization**: See which agents are working and their progress in real-time
- **Trend Selection UI**: Visual cards for selecting Google Search and YouTube trends
- **PDF Upload**: Drag-and-drop or click to upload marketing guide PDFs
- **Activity Timeline**: Track agent processing steps with visual indicators
- **Dark Theme**: Modern, eye-friendly interface for extended use
- **Session Management**: Automatic session creation and persistence

### Frontend Architecture

The frontend is built with modern web technologies:
- **React 19** + **TypeScript** for type-safe component development
- **Vite** for lightning-fast development and hot module replacement
- **Tailwind CSS** for responsive, utility-first styling
- **Server-Sent Events (SSE)** for real-time streaming updates from agents
- **Radix UI** for accessible, unstyled UI components

### Development Guide

To work on the frontend:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── ui/           # Reusable UI components
│   │   ├── WelcomeScreen.tsx
│   │   ├── ChatMessagesView.tsx
│   │   ├── ActivityTimeline.tsx
│   │   └── TrendSelector.tsx
│   ├── App.tsx           # Main application component
│   ├── config.ts         # Configuration settings
│   └── utils.ts          # Utility functions
├── package.json          # Dependencies and scripts
├── vite.config.ts        # Vite configuration
└── tsconfig.json         # TypeScript configuration
```

### API Integration

The frontend communicates with the ADK API server through a proxy configuration in Vite, ensuring seamless development:

- All `/api/*` requests are proxied to `http://localhost:8000`
- Session management is handled automatically
- Real-time updates via SSE for agent responses

### Credits

The frontend implementation is inspired by and adapted from the [Gemini Fullstack example](https://github.com/google/adk-samples/tree/main/python/agents/gemini-fullstack) in Google's ADK samples repository.

## Artifact Server

The application includes a custom artifact server that makes generated images and videos directly accessible via HTTP URLs. This enables:

- **Direct browser access**: View artifacts without base64 decoding
- **Shareable URLs**: Share artifact links that work in any browser
- **Better performance**: Stream large files directly instead of embedding in JSON
- **Content-type handling**: Proper MIME types for images and videos

### How it works

The artifact server (running on port 8001) acts as a proxy between the frontend and ADK's artifact storage:

1. Fetches artifacts from the ADK backend
2. Decodes base64 data with robust error handling
3. Serves files with appropriate content types
4. Provides shareable HTTP URLs for all artifacts

### Artifact URLs

Generated artifacts are accessible at:
```
http://localhost:8001/artifact/trends_and_insights_agent/users/{userId}/sessions/{sessionId}/artifacts/{artifactKey}
```

Example:
```
http://localhost:8001/artifact/trends_and_insights_agent/users/u_999/sessions/abc123/artifacts/Vice_City_Doodle_Drive_0.mp4
```

### Configuration

The artifact server is configured in `frontend/src/config.ts`:
```typescript
artifactUrl: import.meta.env.VITE_ARTIFACT_URL || 'http://localhost:8001'
```

For production deployments, set the `VITE_ARTIFACT_URL` environment variable to your artifact server URL.

## How it works

<details>
  <summary> Example usage </summary>

#### [1] Capture campaign metadata & user-selected trends

Using the new frontend interface:

1. **Start your session**: Type "hello" in the chat interface
2. **Upload campaign guide**: Click "Upload PDF" or drag and drop your marketing guide PDF
3. **Select trends**: Choose from visual cards showing Google Search and YouTube trends
4. **Watch agents work**: See real-time progress as agents research and generate content
5. **Receive results**: Get comprehensive reports and ad campaigns

The agent will interactively guide you through providing:
- Brand information
- Target Product details
- Key Selling Points
- Target Audience demographics

<details>
  <summary> [Optional] preload campaign metadata </summary>

preload these values using one of the example json configs e.g., [shared_libraries/profiles/example_state_pixel.json](trends_and_insights_agent/shared_libraries/profiles/example_state_pixel.json) or upload your own. The json config you wish to reference should be set in your `.env` file like below. *Note: remove or comment out this variable to use default option (1)*

```
SESSION_STATE_JSON_PATH=example_state_prs.json
```
</details>


#### [2] Autonomous research workflow

#### [3] Interactive ad content generator

> Note: this section is configured for **human-in-the-loop** i.e., agent will iterate with user when generating image and video creatives

  - Choose a subset of ad copies to proceed with
  - Choose a subset of visual concepts to proceed with
  - Generate image and video creatives with visual concepts

#### [4] Compile final research and creative report

</details>

## Example ad creatives

<details>
  <summary>Hulkamania & Pixel 9's Call Assist</summary>

<p align="center">
  <img src='media/t2a_hulk_call_Screen_v2.png' width="800"/>
</p>

</details>


<details>
  <summary>Titanic & PRS Guitars</summary>

<p align="center">
  <img src='media/titanic_prs.png' width="800"/>
</p>

</details>


<details>
  <summary>Adam Sandler (Waterboy) & PRS Guitars</summary>

<p align="center">
  <img src='media/waterboy_prs.png' width="800"/>
</p>

</details>


<details>
  <summary>Mad Again & Pixel 9' Call Assist</summary>

<p align="center">
  <img src='media/mad_again_pixel.png' width="800"/>
</p>

</details>



## Video walkthrough

> Updated version coming soon!


## Sub-agents & Tools

### A2A Architecture (Distributed)

When running with a2a server, all agents are managed by a single orchestrator:

```
a2a_orchestrator (server on port 9000)
├── trends_insights
│   ├── Trend selection interface
│   ├── PDF campaign guide extraction
│   └── YouTube video summarization
├── research_orchestrator
│   ├── Parallel research coordination
│   │   ├── YouTube trend analysis
│   │   ├── Google Search trend analysis
│   │   └── Campaign research
│   ├── Research quality evaluation
│   ├── Follow-up search refinement
│   └── Report synthesis with citations
└── ad_generator
    ├── Ad copy generation pipeline
    │   ├── Draft → Critique → Finalize
    ├── Visual concept development
    │   ├── Draft → Critique → Finalize
    └── Media generation (Imagen/Veo)
```

### Classic Architecture (Monolithic)

When running without a2a servers, all agents run in-process:

```
root_agent (orchestrator)
├── trends_and_insights_agent              # Display/capture trend selections
├── research_orchestrator                  # Coordinate research pipeline
│   ├── combined_research_pipeline         # Sub-agent for SequentialAgent workflow
│   │   ├── merge_parallel_insights        # Parallel research coordination
│   │   │   ├── parallel_planner_agent     # Runs 3 research types simultaneously
│   │   │   │   ├── yt_sequential_planner  # YouTube trend analysis
│   │   │   │   ├── gs_sequential_planner  # Google Search trend analysis
│   │   │   │   └── ca_sequential_planner  # Campaign research
│   │   │   └── merge_planners             # Combines research plans
│   │   ├── combined_web_evaluator         # Quality check
│   │   ├── enhanced_combined_searcher     # Expand web search
│   │   └── combined_report_composer       # Generate unified research report
├── ad_content_generator_agent             # Create comprehensive ad campaigns
│   ├── ad_creative_pipeline               # Ad copy actor-critic framework
│   │   ├── ad_copy_drafter
│   │   ├── ad_copy_critic
│   ├── visual_generation_pipeline         # Visual concept actor-critic framework
│   │   ├── visual_concept_drafter
│   │   ├── visual_concept_critic
│   │   └── visual_concept_finalizer
│   └── visual_generator                   # Image/video generation
└── save_creatives_and_research_report     # Compile PDF reports

```

Expand sections below to visualize complex agent workflows

<details>
  <summary>Trend and Insight Agent</summary>

> This agent is responsible for gathering input from the user. 

<p align="center">
  <img src='media/t2a_trend_ast_overview_0725.png' width="800"/>
</p>

</details>


<details>
  <summary>Research Orchestrator Pipeline</summary>

**The research workflow has two phases:**
1. Parallel web research for individual topics: search trend, YouTube video, and campaign metadata e.g., target audience, product, brand, etc.
2. Combined web research for the intersection of individual topics

> This structure helps us achieve a deeper understanding of each subject first. And this helps us ask better questions for a second round of research where we are solely focused on finding any culturally relevant overlaps to exploit for ad creatives. 

<p align="center">
  <img src='media/t2a_research_overview_0725.png' width="800"/>
</p>

</details>


<details>
  <summary>Ad Content Generator Pipeline</summary>

> This agent uses the research report to generate relevant ad copy, visual concepts, and creatives (image and video). 

<p align="center">
  <img src='media/t2a_ad_overview_0725.png' width="800"/>
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

## Deployment to Agentspace


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