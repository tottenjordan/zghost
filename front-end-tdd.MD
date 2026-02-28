


Based on the audio description and the provided screenshots of your Marketing Intelligence application, here is a structured Test-Driven Development (TDD) plan using a Behavior-Driven Development (BDD) style format (Given/When/Then). This format is excellent for mapping out Customer User Journeys (CUJs) before writing the actual code and tests.

### CUJ 1: Campaign Configuration & Trend Selection
**Goal:** A user can configure campaign parameters, upload brand guidelines, asynchronously load trends, and submit the job.

**Describe: Campaign Setup Wizard**
*   **It should asynchronously fetch trends upon initialization.**
    *   **Given** the user navigates to the "Configure" tab (Step 1: Campaign).
    *   **When** the component mounts.
    *   **Then** a loading indicator with the text "Fetching live trends from backend agents..." should be displayed.
    *   **And** the trend fetching process should run in the background without blocking UI interaction.
*   **It should capture all campaign configuration inputs.**
    *   **Given** the user is on the Campaign Setup step.
    *   **When** the user inputs text into the "Brand", "Target Product", "Target Audience", and "Key Selling Points" fields.
    *   **Then** the application state should accurately reflect these inputs.
*   **It should handle brand guideline PDF uploads.**
    *   **Given** the user is on the Campaign Setup step.
    *   **When** the user drags and drops a PDF into the "Campaign Guide" dropzone.
    *   **Then** the file should be accepted, validated as a PDF, and stored in the campaign context.

**Describe: Trend Discovery & Review**
*   **It should allow users to select relevant trends.**
    *   **Given** the asynchronous trend fetching has completed.
    *   **When** the user navigates to the "Trends" step.
    *   **Then** a list of populated trends (e.g., Google Search, YouTube) should be visible.
    *   **When** the user toggles specific trends.
    *   **Then** the selected trends should be added to the campaign state.
*   **It should display a summary before job execution.**
    *   **Given** the user has completed setup and selected trends.
    *   **When** the user navigates to the "Review" step.
    *   **Then** a "Campaign Summary" should accurately display the inputted Brand, Product, Audience, and Selling Points.
    *   **And** a "Selected Trends" section should list the exactly chosen Google and YouTube trends.
*   **It should dispatch the job to the orchestrator.**
    *   **Given** the user is on the final Review step.
    *   **When** the user clicks the final confirm/run button.
    *   **Then** a new job payload containing all configuration and selected trends should be submitted to the backend orchestrator.

---

### CUJ 2: Orchestration & Job Monitoring
**Goal:** Super users can monitor the execution of jobs through a timeline and view real-time state.

**Describe: Orchestrator Dashboard**
*   **It should restrict access to super users.**
    *   **Given** a standard user attempts to view the full orchestrator view.
    *   **Then** they should be denied access or shown a restricted view.
    *   **Given** a super user accesses the Orchestration tab.
    *   **Then** they should see the full monitoring dashboard.
*   **It should visualize running agents on a timeline.**
    *   **Given** a job has been dispatched and is running.
    *   **When** the super user views the "Timeline" or "Agent Graph".
    *   **Then** active processes like "Trend Discovery," "Market Research," and "Ad Creative" should be displayed as running bars.
    *   **And** the status of individual sub-agents (e.g., "YouTube Planner", "Web Evaluator") should update dynamically (e.g., pending, running, complete).
*   **It should expose the real-time session state.**
    *   **Given** the orchestrator is running a session.
    *   **When** the user views the "Session State" side panel.
    *   **Then** current variables such as `brand`, `campaign_web_search_insights`, and `commercial_duration` should be visible and update as agents mutate the state.

---

### CUJ 3: Artifact Generation, Review & Evaluation
**Goal:** Users can manage evaluation rubrics, review generated narratives, direct video content, and evaluate the final outputs.

**Describe: Rubric Management (Configuration Phase)**
*   **It should allow activation of evaluation criteria.**
    *   **Given** the user navigates to the "Rating & Evaluation" configuration.
    *   **When** the user views the "Rubric Library".
    *   **Then** a list of available rubrics (e.g., "Ad Copy Quality", "Commercial Production") should be visible.
    *   **When** the user clicks "Activate for Pipeline" on a specific rubric.
    *   **Then** the pipeline rubric configuration should update to include that active criteria.

**Describe: Narrative Studio**
*   **It should facilitate feedback on generated text.**
    *   **Given** the orchestration job has generated a PDF narrative.
    *   **When** the user navigates to the "Narrative" tab.
    *   **Then** the generated PDF should be rendered in the view.
    *   **When** the user submits text feedback on the document.
    *   **Then** the feedback should be saved to the database to inform future generation iterations.

**Describe: AV Studio**
*   **It should integrate Veo-generated clips.**
    *   **Given** the visual generation pipeline has completed.
    *   **When** the user navigates to the "AV Studio" tab.
    *   **Then** the video clips generated by Veo should be loaded into the media bin.
    *   **When** the user interacts with the directing tools (e.g., timeline arrangement, sequencing).
    *   **Then** the edits should be reflected in the final video composition state.

**Describe: Evaluation Studio**
*   **It should present dual evaluation metrics (LLM & Human).**
    *   **Given** an artifact has been generated and the active rubrics have been applied by the LLM.
    *   **When** the user navigates to the "Evaluation Studio" tab.
    *   **Then** the LLM's automated scores and reasoning based on the rubric should be displayed.
    *   **When** the user inputs their manual evaluation scores and comments.
    *   **Then** both the LLM evaluation and the human evaluation should be persisted alongside the generated artifact.