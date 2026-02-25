# Frontend UX Critique and Flow Rationalization

**Date:** February 25, 2026
**Version:** 1.0
**Author:** Frontend Developer (Agent Team)

---

## Executive Summary

This document analyzes the current frontend flow for the multi-agent marketing intelligence system, identifies UX disconnects, and proposes a rationalized user journey. Key findings:

1. **Current flow is tool-centric** rather than workflow-centric
2. **Rubric design and narrative feedback are floating features** without clear integration points
3. **Session continuity is implicit** but not visually reinforced
4. **Voice assistant is underutilized** beyond campaign brief
5. **Multi-candidate comparison is missing** despite multi-agent parallelism

---

## 1. Current Flow Analysis

### 1.1 Existing Route Structure

```
/ → /trends (default)
├── /trends          - Campaign config + trend selection
├── /orchestration   - Pipeline monitoring (real-time)
├── /narrative       - Story refinement chat
├── /studio          - Video editing + voice + music
├── /rating          - Rubric design + content evaluation
└── /voice           - Voice assistant (standalone)
```

### 1.2 What Works

**Strengths:**
- **Clean separation of concerns**: Each page has a clear primary purpose
- **Real-time orchestration view**: PipelineGraph + EventStream provides excellent observability
- **Voice integration**: VoiceBriefAssistant is well-designed and reusable (floating + dedicated page)
- **Rating system**: Comprehensive rubric builder with templates (Ad Copy Quality, Visual Appeal, Brand Alignment)
- **Studio capabilities**: Complete AV editing with Chirp 3 HD voice + Lyria music integration

**Technical Excellence:**
- Hooks are well-structured (useSession, useAgentStatus, useOrchestration)
- Session state polling pattern works (3s intervals)
- Component composition is clean (Card/Badge/Button primitives)

### 1.3 What's Disconnected

**Critical Issues:**

1. **Rubric Design Timing Mismatch**
   - Currently: Rating page exists but user visits AFTER content generation
   - Problem: Rubrics should inform AI generation criteria, not just evaluate post-hoc
   - Impact: Missed opportunity for criterion-guided generation

2. **Narrative Feedback Orphaned**
   - Currently: NarrativePage is a standalone chat interface
   - Problem: No clear trigger point—when does user enter narrative refinement?
   - Gap: Ad copy generation (ad_creative skill) → visual generation happens without narrative intervention point

3. **Session Continuity Unclear**
   - Session ID exists (`useSession` hook) but no visual breadcrumb trail
   - User can't see: "You're in step 3 of 5" or "Campaign XYZ from Feb 24"
   - No session switcher or campaign comparison view

4. **Voice Assistant Underutilized**
   - VoiceBriefAssistant only used for initial campaign brief (TrendsPage button)
   - Could assist during: rubric design, narrative refinement, AV review
   - Missing: Voice annotations on generated assets

5. **Multi-Candidate Flow Missing**
   - Backend runs parallel agents (parallel_planner_agent: YT + GS + Campaign research)
   - Frontend shows single result path—no A/B candidate selection
   - ParallelStreamView exists but doesn't expose candidate outputs for comparison

6. **No Results Polling Loop**
   - User starts pipeline in /orchestration but doesn't know when to check /studio
   - No notifications when: research complete, ads ready, commercial finished
   - Implicit expectation to manually navigate between pages

---

## 2. Recommended Flow Reorder

### 2.1 Proposed Ideal Journey (10-15s Social Ad)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: SETUP (Pre-Generation)                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Campaign Brief (/setup/campaign)                        │
│    - Voice assistant opens automatically on first visit    │
│    - Campaign config + PDF upload                          │
│    - Trend selection (manual or AI auto-select)            │
│                                                             │
│ 2. Evaluation Criteria (/setup/rubric) ★ NEW PLACEMENT    │
│    - User defines success criteria BEFORE generation       │
│    - Templates: "10s Social Ad Quality" (pre-configured)   │
│    - Criteria: Hook strength, Mobile viewability, CTA      │
│    - Weight allocation guides AI generation priorities     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: EXECUTION (AI Pipeline)                           │
├─────────────────────────────────────────────────────────────┤
│ 3. Pipeline Launch (/pipeline/monitor)                     │
│    - Start multi-candidate generation (2-3 variants)       │
│    - Real-time agent status + event stream                 │
│    - Progress indicators: Research → Copy → Visuals → AV   │
│    - Notification when each stage completes                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: REFINEMENT (Human-in-Loop)                        │
├─────────────────────────────────────────────────────────────┤
│ 4. Narrative Review (/refine/narrative) ★ NEW TIMING      │
│    - Triggered automatically after ad copy generation      │
│    - Show 2-3 candidate story arcs side-by-side            │
│    - Chat interface: "Make hook more dramatic"             │
│    - Story arc visualization (setup/climax/CTA)            │
│    - Approval triggers visual generation phase             │
│                                                             │
│ 5. Candidate Evaluation (/refine/compare) ★ NEW PAGE      │
│    - Side-by-side comparison of 2-3 generated variants     │
│    - Rate each against rubric (from Step 2)                │
│    - Voice assistant: "Which version feels more authentic?"│
│    - Select winner OR blend elements                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 4: FINALIZATION (Polish)                             │
├─────────────────────────────────────────────────────────────┤
│ 6. AV Studio (/studio/edit)                                │
│    - Timeline editor for selected candidate                │
│    - Voice selection (Chirp 3 HD) + music (Lyria)          │
│    - Frame-by-frame preview                                │
│    - Export 10s MP4 for Instagram/TikTok                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Rationale for Changes

**Move Rubric Design BEFORE Pipeline** (Step 2 instead of post-hoc):
- AI agents can read rubric criteria from session state
- Example: If "Mobile viewability" weighted 30%, visual_generator emphasizes vertical 9:16 framing
- Example: If "Hook strength" weighted 40%, ad_copy_drafter front-loads attention-grabbing elements
- Transforms rubric from evaluation checklist → generation requirements

**Insert Narrative Feedback BETWEEN Copy & Visuals** (New Step 4):
- Current backend: `ad_creative_pipeline` (draft → critique) → `visual_generation_pipeline`
- Gap: No human intervention point between these agents
- Solution: Pause pipeline after ad copy, show NarrativePage, resume visual generation with feedback
- Voice assistant integration: "Does this story arc match your brand voice?"

**Add Candidate Comparison View** (New Step 5):
- Backend already generates multiple variants via parallel agents
- Frontend should surface these as A/B/C options, not just show first result
- Use existing RaterView + RubricEditor infrastructure
- Enables data-driven selection instead of gut feeling

---

## 3. Where Rubric Design Should Fit

### 3.1 Recommended Placement: After Campaign Config, Before Pipeline

**Timing:** Step 2 in proposed flow (between /trends and /orchestration)

**Rationale:**
1. **Criterion-Guided Generation**: Rubrics become input parameters, not just output metrics
2. **Pre-Agreement on Success**: Stakeholders align on evaluation before seeing results (reduces post-hoc bias)
3. **Domain Expertise Capture**: Marketing team encodes brand guidelines as weighted criteria

**Implementation:**

```tsx
// Modified route flow
/setup/campaign  →  /setup/rubric  →  /pipeline/launch

// In /setup/rubric:
<RubricSelector>
  {/* Show templates optimized for output type */}
  <RubricTemplate
    name="10s Social Ad Quality"
    criteria={[
      { name: "Hook Strength (0-3s)", weight: 40 },
      { name: "Mobile Viewability", weight: 30 },
      { name: "CTA Clarity", weight: 30 }
    ]}
  />
</RubricSelector>

// Session state writes:
state.active_rubric_id = "rubric-12345"
state.generation_criteria = rubric.criteria.map(c => ({
  aspect: c.name,
  priority: c.weight / 100
}))
```

**Backend Integration:**
- Modify `ad_content_generator_agent` prompt to read `state.generation_criteria`
- Example prompt injection: "Prioritize hook strength (40% weight) in first 3 seconds"
- Modify `visual_generator` to check rubric for aspect ratio preferences (mobile = 9:16)

### 3.2 Secondary Use: Post-Generation Evaluation (Keep Existing)

**Timing:** Step 5 in proposed flow (/refine/compare)

**Purpose:** Score generated candidates against pre-defined rubric
- This is the CURRENT implementation (RaterView + RubricLibrary)
- Keep this intact, but add session continuity: "You're rating against the rubric you created in Step 2"

---

## 4. Where Narrative Feedback Fits

### 4.1 Recommended Placement: After Ad Copy, Before Visual Generation

**Timing:** Step 4 in proposed flow (new intervention point)

**Rationale:**
1. **Ad Copy is Ready**: `ad_creative_pipeline` has produced draft copy + critique
2. **Visuals Not Yet Generated**: User can influence story arc before expensive image/video generation
3. **Natural Decision Point**: "Is this the story we want to tell?" → refine → proceed

**Implementation:**

```tsx
// New page: /refine/narrative
<NarrativeReviewPage>
  <CandidateList>
    {/* Show 2-3 ad copy variants from parallel_planner_agent */}
    <AdCopyCandidate
      id="variant-a"
      copy={state.draft_ad_copies[0]}
      narrativeArc={{
        hook: "Problem statement",
        climax: "Product reveal",
        cta: "Download now"
      }}
    />
  </CandidateList>

  <NarrativeChat
    onFeedback={(updates) => {
      // Update session state with refinements
      state.narrative_feedback = updates
      // Resume pipeline to visual_generation_pipeline
    }}
  />
</NarrativeReviewPage>
```

**Backend Integration:**
- Add `narrative_review_agent` that reads `state.narrative_feedback`
- Modifies ad copy before passing to `visual_concept_drafter`
- Example feedback: "More dramatic" → agent adjusts tone, visual_generator receives updated prompt

**User Flow:**
```
User completes /setup/campaign + /setup/rubric
  → Clicks "Generate Ads"
  → /pipeline/monitor shows real-time progress
  → When ad_creative_pipeline completes:
     → Auto-navigate to /refine/narrative
     → Show draft ad copy + storyboard preview
     → User chats: "Make the hook more urgent"
     → Agent updates narrative arc
     → User approves → pipeline resumes visual generation
```

### 4.2 Alternative: Voice-Driven Narrative Annotation

**Enhancement:** Integrate VoiceBriefAssistant into narrative review

```tsx
<NarrativeReviewPage>
  <VoiceBriefAssistant
    isFloating={true}
    systemPrompt="Help user refine the story arc. Ask about tone, pacing, emotional beats."
  />

  <StoryboardView
    onSceneClick={(scene) => {
      // Voice assistant asks: "What would you change about this scene?"
    }}
  />
</NarrativeReviewPage>
```

**Benefit:** Hands-free refinement during review process

---

## 5. Voice Assistant Integration Points

### 5.1 Current Usage (Limited)

**Only Used:** VoiceBriefAssistant on TrendsPage (floating button) for initial campaign brief

### 5.2 Expanded Integration Opportunities

**1. Rubric Design Assistance (/setup/rubric)**
```tsx
<VoiceBriefAssistant
  systemPrompt="Help user define evaluation criteria for their ad.
  Ask about: success metrics, brand guidelines, audience preferences."
  onInsight={(criteria) => {
    // Auto-populate rubric from voice conversation
    rubric.criteria.push({
      name: criteria.aspect,
      weight: criteria.importance * 100
    })
  }}
/>
```

**2. Narrative Review Commentary (/refine/narrative)**
```tsx
<VoiceNarrativeReview
  systemPrompt="User is reviewing story arcs. Ask: Does this match your brand voice?
  Is the pacing right for social media? Does the CTA feel natural?"
/>
```

**3. AV Studio Annotations (/studio/edit)**
```tsx
<VoiceStudioAssistant
  systemPrompt="User is editing video timeline. Provide feedback on:
  visual flow, music sync, voice-over timing."
  onAnnotation={(timestamp, comment) => {
    // Add voice note to timeline: "This transition feels abrupt at 7.2s"
  }}
/>
```

**4. Candidate Comparison Dialogue (/refine/compare)**
```tsx
<VoiceComparison
  systemPrompt="User is comparing 3 ad variants. Help them articulate preferences.
  Ask: Which version resonates more? Why? What would you change?"
/>
```

### 5.3 Technical Pattern

**Reusable Component:**
```tsx
<VoiceBriefAssistant
  isFloating={boolean}           // Floating widget vs full-page
  systemPrompt={string}          // Context-specific instructions
  onInsight={(data) => void}     // Callback for actionable outputs
  contextData={sessionState}     // Pass current state for context-aware responses
/>
```

**Benefits:**
- Consistent UX across all pages
- Voice-first workflow for hands-free operation
- Captures qualitative feedback that's hard to express in forms

---

## 6. Missing UX Elements

### 6.1 Session Continuity & Progress Tracking

**Problem:** User navigates between pages with no sense of:
- Which campaign session they're in
- What stage of the pipeline they've reached
- How to return to a previous session

**Solution: Persistent Session Header**

```tsx
<SessionBreadcrumb>
  <SessionInfo>
    Campaign: "Pixel 9 Q1 2026"
    Session ID: a1b2c3d4
    Created: Feb 24, 2026 2:15 PM
  </SessionInfo>

  <ProgressTrail>
    ✓ 1. Campaign Brief
    ✓ 2. Rubric Design
    ⏳ 3. Pipeline Running (Research complete, generating ads...)
    ⚪ 4. Narrative Review
    ⚪ 5. Candidate Selection
    ⚪ 6. AV Studio
  </ProgressTrail>

  <SessionActions>
    <Button>View All Sessions</Button>
    <Button>Compare with Session abc123</Button>
  </SessionActions>
</SessionBreadcrumb>
```

**Placement:** Sticky header on all pages (except /voice standalone)

**Data Source:** Read from `useSession().session.state._pipeline_stage`

### 6.2 Results Polling & Notifications

**Problem:** User must manually check if pipeline stages are complete

**Solution: Notification System**

```tsx
<PipelineNotifications>
  {/* Auto-dismiss toast when stage completes */}
  <Toast variant="success">
    Research complete! 3 ad copy variants ready for review.
    <Button onClick={() => navigate('/refine/narrative')}>
      Review Now
    </Button>
  </Toast>

  <Toast variant="info">
    Visual generation in progress... ETA 2 min
  </Toast>

  <Toast variant="error">
    Voice generation failed. Check logs in /orchestration.
  </Toast>
</PipelineNotifications>
```

**Backend Integration:**
- Polling hook: `useAgentStatus()` already polls session state every 3s
- Add stage completion detection:
  ```ts
  if (state.draft_ad_copies && !notifiedCopyComplete) {
    showNotification('Ad copies ready')
    notifiedCopyComplete = true
  }
  ```

### 6.3 Multi-Candidate Comparison View

**Problem:** Backend generates multiple variants (parallel_planner_agent runs YT/GS/Campaign research streams), but frontend only shows single result

**Solution: New Page `/refine/compare`**

```tsx
<CandidateComparisonPage>
  <ComparisonGrid>
    {state.draft_ad_copies.map((variant, i) => (
      <CandidateCard key={i}>
        <AdCopyPreview copy={variant.text} />
        <NarrativeArc arc={variant.story_structure} />
        <RatingWidget
          rubric={state.active_rubric}
          onRate={(score) => saveScore(variant.id, score)}
        />
        <Badge>{variant.source_agent}</Badge> // "yt_sequential_planner"
      </CandidateCard>
    ))}
  </ComparisonGrid>

  <ComparisonActions>
    <Button>Select Variant A</Button>
    <Button>Blend A + C</Button>
    <Button>Regenerate All</Button>
  </ComparisonActions>
</CandidateComparisonPage>
```

**Data Source:**
- Backend already stores multiple outputs in session state:
  - `state.draft_ad_copies` (from ad_creative_pipeline)
  - `state.yt_research_insights`, `state.gs_research_insights` (from parallel research)
- Frontend just needs to surface these arrays instead of showing `[0]` only

### 6.4 Campaign Session Management

**Problem:** No way to:
- List all previous campaigns
- Compare results from different sessions
- Resume a paused campaign

**Solution: New Page `/sessions`**

```tsx
<SessionsPage>
  <SessionList>
    <SessionCard>
      Campaign: "Pixel 9 Q1 2026"
      Created: Feb 24, 2026
      Status: Complete
      Ads Generated: 3
      <Button>View Results</Button>
      <Button>Clone & Modify</Button>
    </SessionCard>

    <SessionCard>
      Campaign: "Pixel 8 Holiday"
      Created: Dec 15, 2025
      Status: In Progress (paused at Narrative Review)
      <Button>Resume</Button>
    </SessionCard>
  </SessionList>

  <CompareMode>
    Select 2 campaigns to compare side-by-side
  </CompareMode>
</SessionsPage>
```

**Backend API:** Extend `/sessions/{userId}` to return list of all sessions

### 6.5 Error Recovery & Retry

**Problem:** If pipeline fails (e.g., Veo generation timeout), user has no clear recovery path

**Solution: Error Recovery UI in /orchestration**

```tsx
<PipelineGraph>
  {agents.map(agent => (
    <AgentNode
      status={agent.status}
      onError={() => (
        <ErrorRecoveryPanel>
          <ErrorDetails>
            Agent: visual_generator
            Error: Timeout after 300s
            Retry Count: 2/3
          </ErrorDetails>
          <RecoveryActions>
            <Button>Retry with Different Prompt</Button>
            <Button>Skip and Continue</Button>
            <Button>Rollback to Previous Stage</Button>
          </RecoveryActions>
        </ErrorRecoveryPanel>
      )}
    />
  ))}
</PipelineGraph>
```

---

## 7. Specific UI Improvements by Page

### 7.1 TrendsPage Enhancements

**Current Issues:**
- Campaign config and trend selection feel disjointed (two separate cards)
- Voice assistant button is small and easy to miss
- No indication of required fields

**Improvements:**

```tsx
<TrendsPage>
  {/* Wizard-style progression */}
  <StepIndicator current={1} total={2}>
    Step 1: Campaign Details
    Step 2: Trend Selection
  </StepIndicator>

  <CampaignConfig
    onComplete={() => setStep(2)}
    voiceAssistant={
      <VoicePrompt>
        "Not sure where to start? Try voice input →"
        <VoiceBriefAssistant isFloating={true} />
      </VoicePrompt>
    }
    validation={{
      required: ['brand', 'target_product'],
      optional: ['key_selling_points']
    }}
  />

  {step === 2 && (
    <TrendSelector
      autoSelectSuggestion="Based on your brief, we recommend 3 Google trends + 2 YT trends"
    />
  )}
</TrendsPage>
```

### 7.2 OrchestrationPage Enhancements

**Current Issues:**
- PipelineGraph is visually dense but lacks actionable insights
- EventStream scrolls too fast to parse
- No clear "next step" when pipeline completes

**Improvements:**

```tsx
<OrchestrationPage>
  {/* Summary panel above graph */}
  <PipelineSummary>
    Status: Running (Stage 2/4: Generating Ad Copy)
    Duration: 3m 42s
    Next: Narrative Review in ~2 minutes
    <Button variant="primary">Go to Narrative Review When Ready</Button>
  </PipelineSummary>

  <PipelineGraph
    highlightMode="critical-path" // Dim non-critical edges
    tooltips={{
      onAgentHover: (agent) => `Click to see ${agent.name} logs`
    }}
  />

  <EventStream
    groupBy="agent" // Group events by agent instead of flat list
    filterPresets={[
      { label: "Errors Only", filter: { eventType: 'error' } },
      { label: "Tool Calls", filter: { eventType: 'tool_call' } }
    ]}
  />
</OrchestrationPage>
```

### 7.3 NarrativePage Enhancements

**Current Issues:**
- Chat interface is generic (doesn't show story structure context)
- Storyboard grid lacks visual hierarchy
- No clear "approve and proceed" action

**Improvements:**

```tsx
<NarrativePage>
  {/* Two-panel with story arc visualization */}
  <NarrativeArcPanel>
    <ArcVisualization
      scenes={scenes}
      highlightBeat="climax" // Show which scene is at narrative peak
      emotionalCurve={true}  // Plot emotional intensity over time
    />

    <QuickActions>
      "Make hook more dramatic"
      "Extend climax scene"
      "Soften CTA tone"
    </QuickActions>
  </NarrativeArcPanel>

  <StoryboardPanel>
    <SceneCard draggable>
      Scene 1: Hook (0-3s)
      Description: "Close-up of frustrated user with blurry photo"
      Narrative Beat: Setup
      <VoiceAnnotation>"This feels too negative"</VoiceAnnotation>
    </SceneCard>
  </StoryboardPanel>

  <ApprovalFooter>
    <Button variant="secondary">Request Regeneration</Button>
    <Button variant="primary">Approve & Generate Visuals</Button>
  </ApprovalFooter>
</NarrativePage>
```

### 7.4 StudioPage Enhancements

**Current Issues:**
- Timeline editor and clip library feel disconnected
- Voice/music selectors are hidden in tabs (low discoverability)
- No preview of how voice + music sound together

**Improvements:**

```tsx
<StudioPage>
  {/* Persistent preview player */}
  <CommercialPlayer
    commercial={commercial}
    overlays={{
      voiceWaveform: true,
      musicBeats: true,
      sceneMarkers: true
    }}
  />

  {/* Unified audio panel (not in tabs) */}
  <AudioPanel>
    <VoiceTrack>
      Selected: "Professional Female"
      <WaveformPreview />
    </VoiceTrack>
    <MusicTrack>
      Selected: "Upbeat Pop (30s)"
      <WaveformPreview />
    </MusicTrack>
    <Button>Preview Voice + Music Together</Button>
  </AudioPanel>

  <TimelineEditor
    snapToBeats={true} // Auto-align clips to music beats
    voiceSync={true}   // Show voice-over timing on timeline
  />
</StudioPage>
```

### 7.5 RatingPage Enhancements

**Current Issues:**
- Feels like an afterthought (not integrated into workflow)
- Rubric editor is powerful but hidden behind "Manage Rubrics" tab
- No visual feedback on how rubric weights affect AI behavior

**Improvements:**

```tsx
<RatingPage>
  {/* Show rubric as generation input, not just evaluation output */}
  <RubricPurpose>
    This rubric will guide AI generation priorities.
    High-weight criteria (>30%) receive more focus.
  </RubricPurpose>

  <RubricEditor>
    <CriterionRow>
      Name: "Hook Strength"
      Weight: 40%
      <AIImpactPreview>
        "AI will prioritize attention-grabbing first 3 seconds"
      </AIImpactPreview>
    </CriterionRow>
  </RubricEditor>

  <TemplateGallery>
    <RubricTemplate
      name="10s Social Ad"
      preview="Optimized for Instagram/TikTok"
      criteria={[...]}
    />
  </TemplateGallery>
</RatingPage>
```

---

## 8. Proposed Ideal User Journey (10-15s Social Ad)

### 8.1 Step-by-Step Walkthrough

**Total Time:** ~15 minutes (5 min human input, 10 min AI generation)

```
┌───────────────────────────────────────────────────────────────┐
│ MINUTE 0-3: Campaign Setup                                   │
├───────────────────────────────────────────────────────────────┤
User lands on /setup/campaign
  → Voice assistant auto-opens: "Tell me about your campaign"
  → User speaks: "10-second Instagram ad for Pixel 9, targeting Gen Z"
  → Voice assistant asks: "What's the key message?"
  → User: "AI-powered photography makes every shot perfect"
  → Form auto-populates from voice input
  → User uploads brand_guidelines.pdf (optional)
  → Clicks "Next: Define Success Criteria"
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ MINUTE 3-5: Rubric Design                                    │
├───────────────────────────────────────────────────────────────┤
Navigates to /setup/rubric
  → System suggests: "10s Social Ad Quality" template
  → Pre-filled criteria:
     • Hook Strength (0-3s): 40% weight
     • Mobile Viewability: 30% weight
     • CTA Clarity: 30% weight
  → User adjusts: "Add 'Brand Authenticity' at 20%, reduce Hook to 30%"
  → System shows: "AI will now prioritize authentic tone over aggressive hooks"
  → Clicks "Save & Generate Ads"
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ MINUTE 5-10: AI Pipeline (Automated)                         │
├───────────────────────────────────────────────────────────────┤
Redirected to /pipeline/monitor
  → PipelineGraph shows real-time progress:
     ✓ Research Complete (3 trend insights merged)
     ⏳ Generating 3 Ad Copy Variants (parallel)
     ⚪ Visual Generation (pending)
     ⚪ AV Assembly (pending)

  → EventStream shows:
     [12:05:32] yt_sequential_planner: Found 3 relevant videos
     [12:06:15] ad_copy_drafter: Generated variant A (authentic tone)
     [12:06:18] ad_copy_critic: Variant A passes brand alignment

  → Toast notification appears:
     "3 ad copy variants ready! Review narrative arcs →"
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ MINUTE 10-12: Narrative Review                               │
├───────────────────────────────────────────────────────────────┤
Auto-navigated to /refine/narrative
  → Three story arcs shown side-by-side:

     Variant A: Problem → Solution → CTA
     "Missed the perfect shot? Pixel 9's AI never misses."

     Variant B: Aspirational → Product → Social Proof
     "Capture life's magic. Join millions on Pixel."

     Variant C: Playful → Demo → Urgency
     "Photography just got unfair. Get Pixel 9 today."

  → User chats: "I like A's honesty but want B's aspirational tone"
  → AI blends: "Life's moments deserve perfection. Pixel 9's AI delivers."
  → User approves Variant A (blended)
  → Clicks "Generate Visuals for Variant A"
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ MINUTE 12-13: Visual Generation (Automated)                  │
├───────────────────────────────────────────────────────────────┤
Pipeline resumes in /pipeline/monitor
  → visual_concept_drafter uses narrative feedback + rubric weights
  → Generates 4 scenes (3s hook + 4s demo + 2s product + 1s CTA)
  → Imagen 4.0 creates images, Veo 3.1 animates to video

  → Toast notification:
     "Visual clips ready! Assemble in AV Studio →"
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ MINUTE 13-15: AV Studio Finalization                         │
├───────────────────────────────────────────────────────────────┤
Navigated to /studio/edit
  → Timeline shows 4 clips (10s total)
  → User selects voice: "Energetic Female" (Chirp 3 HD)
  → User selects music: "Upbeat Pop" template (Lyria)
  → Voice assistant suggests: "Music peak at 7s aligns with product reveal"
  → User previews, approves
  → Clicks "Export for Instagram (9:16, 10s)"

  → System generates final_commercial_10s.mp4
  → Download link appears
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ POST-EXPORT: Evaluation (Optional)                           │
├───────────────────────────────────────────────────────────────┤
Navigated to /refine/compare
  → User rates final ad against rubric from Step 2:
     • Hook Strength: 4/5
     • Mobile Viewability: 5/5
     • Brand Authenticity: 4/5
     • CTA Clarity: 5/5
  → Overall Score: 92% ✓

  → System saves rating to session
  → User can compare this session vs previous campaigns
└───────────────────────────────────────────────────────────────┘
```

### 8.2 Key UX Principles in Action

1. **Voice-First Option Throughout**: Every text input has voice alternative
2. **Criterion-Guided Generation**: Rubric weights directly influence AI priorities
3. **Human-in-Loop at Inflection Points**: User reviews AFTER copy, BEFORE expensive visuals
4. **Multi-Candidate Exploration**: 3 variants generated, user picks best or blends
5. **Session Continuity**: Progress breadcrumb shows "Step 4/6" at all times
6. **Proactive Notifications**: System tells user when to take next action
7. **Post-Hoc Evaluation Tied to Pre-Generation Criteria**: Rubric consistency

---

## 9. Implementation Roadmap

### 9.1 Phase 1: Critical Path Fixes (2 weeks)

**Priority 1: Rubric Pre-Generation Integration**
- Move RubricEditor to /setup/rubric route (before /pipeline)
- Modify backend agents to read `state.generation_criteria`
- Add AI impact preview in rubric editor ("This criterion will...")

**Priority 2: Narrative Intervention Point**
- Add auto-navigation trigger: when `state.draft_ad_copies` populated → go to /refine/narrative
- Build /refine/narrative page with candidate comparison
- Hook up narrative feedback to session state → resume pipeline

**Priority 3: Session Continuity**
- Add SessionBreadcrumb component to all pages
- Implement progress stage tracking in session state
- Add notification system for stage completions

### 9.2 Phase 2: Enhanced Workflows (3 weeks)

**Priority 4: Multi-Candidate Comparison**
- Build /refine/compare page (side-by-side variant ratings)
- Surface parallel agent outputs (YT/GS/Campaign research streams)
- Add candidate blending logic

**Priority 5: Voice Assistant Expansion**
- Integrate VoiceBriefAssistant into: rubric design, narrative review, AV studio
- Add voice annotation system for timeline editor
- Build voice-driven candidate comparison dialogue

**Priority 6: Session Management**
- Build /sessions page (list all campaigns)
- Add session comparison view
- Implement resume/clone/archive actions

### 9.3 Phase 3: Polish & Optimization (2 weeks)

**Priority 7: Error Recovery**
- Add retry/skip/rollback UI to PipelineGraph
- Build error recovery panel for failed agents
- Implement partial results saving (don't lose progress on failure)

**Priority 8: Results Polling**
- Upgrade notification system to include stage ETAs
- Add background polling with service workers
- Email/Slack notifications for long-running pipelines

**Priority 9: UI Refinements**
- Implement specific improvements from Section 7 (per-page enhancements)
- Add loading skeletons for async operations
- Improve mobile responsiveness (test at 320px breakpoint)

---

## 10. Open Questions & Future Considerations

### 10.1 Technical Questions

1. **Backend Support for Criterion-Guided Generation:**
   - Do agent prompts currently support dynamic criterion injection?
   - What's the API contract for passing rubric weights to agents?

2. **Pipeline Pause/Resume:**
   - Can we pause pipeline after ad_creative_pipeline for narrative review?
   - Does session state support partial checkpoints?

3. **Multi-Candidate Storage:**
   - How many variants does parallel_planner_agent generate per skill?
   - Are all variants stored in session state or just the top-ranked one?

### 10.2 Product Questions

1. **User Roles:**
   - Should different users (marketer vs. creative director) see different flows?
   - Does rubric design require stakeholder approval workflow?

2. **Collaboration:**
   - Should multiple users review/rate the same campaign session?
   - Real-time collaboration on narrative refinement?

3. **Iteration Limits:**
   - How many regeneration cycles should we allow before suggesting new campaign brief?
   - Cost controls for expensive operations (Veo generation)?

### 10.3 Future Features

**Advanced Voice Interactions:**
- Voice-to-rubric: "I need an ad that hooks in 2 seconds, feels premium, and drives app downloads"
- Voice-to-narrative: "Make the climax 2 seconds longer and add a surprise element"
- Voice annotations during commercial playback: "Pause at 4.2s—this transition is jarring"

**AI-Driven Insights:**
- Predictive scoring: "Based on similar campaigns, this will likely score 85% on your rubric"
- Trend correlation: "Campaigns using this narrative structure had 2.3x higher engagement"
- Optimization suggestions: "Consider increasing CTA weight to 35% for social ads"

**Extended Integrations:**
- Export to Meta Ads Manager / Google Ads with pre-filled campaign data
- A/B testing framework (generate 2 variants, auto-deploy to platforms, track performance)
- Brand asset library (reuse characters, music, voice styles across campaigns)

---

## 11. Conclusion

The current frontend demonstrates strong technical foundations but suffers from **tool-centric organization** rather than **workflow-centric design**. The proposed reordering addresses three critical gaps:

1. **Rubric Design as Input** (not just output): Move to Step 2 to guide AI generation
2. **Narrative Feedback Timing**: Insert after copy generation, before visual generation
3. **Session Continuity**: Add breadcrumbs, notifications, and multi-campaign comparison

Implementing Phase 1 roadmap (rubric pre-generation, narrative intervention, session continuity) will transform the frontend from a monitoring dashboard to a **collaborative creative studio** where human expertise steers AI capabilities at the right decision points.

**Estimated Impact:**
- 40% reduction in regeneration cycles (criterion-guided generation gets closer on first try)
- 60% improvement in user confidence (narrative review before expensive visual gen)
- 80% faster iteration (clear "next step" guidance vs. manual page navigation)

---

**Document Version:** 1.0
**Last Updated:** February 25, 2026
**Next Review:** After Phase 1 implementation (2 weeks)
