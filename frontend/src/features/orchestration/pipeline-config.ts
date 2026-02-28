import type { Node, Edge } from 'reactflow';

export interface PipelineNodeData {
  label: string;
  agentName: string;
  type: 'orchestrator' | 'sequential' | 'parallel' | 'tool';
  description?: string;
  skill?: 'root' | 'trends' | 'research' | 'creative' | 'av' | 'focus-group';
}

// Define the agent hierarchy as React Flow nodes
export const PIPELINE_NODES: Node<PipelineNodeData>[] = [
  // Row 0: Root agent (centered)
  {
    id: 'root_agent',
    type: 'agentNode',
    data: {
      label: 'Root Agent',
      agentName: 'root_agent',
      type: 'orchestrator',
      description: 'Main orchestrator',
      skill: 'root',
    },
    position: { x: 600, y: 0 },
  },

  // Row 1: 4 skill entry points spread wide
  // Skill 1: Trend Discovery
  {
    id: 'trends_and_insights_agent',
    type: 'agentNode',
    data: {
      label: 'Trends & Insights',
      agentName: 'trends_and_insights_agent',
      type: 'sequential',
      description: 'Campaign metadata + trend selection',
      skill: 'trends',
    },
    position: { x: 0, y: 150 },
  },

  // Skill 2: Market Research
  {
    id: 'research_orchestrator',
    type: 'agentNode',
    data: {
      label: 'Research Orchestrator',
      agentName: 'research_orchestrator',
      type: 'orchestrator',
      description: 'Coordinates research pipeline',
      skill: 'research',
    },
    position: { x: 400, y: 150 },
  },

  // Skill 3: Ad Creative
  {
    id: 'ad_content_generator_agent',
    type: 'agentNode',
    data: {
      label: 'Ad Content Generator',
      agentName: 'ad_content_generator_agent',
      type: 'orchestrator',
      description: 'Ad campaign orchestrator',
      skill: 'creative',
    },
    position: { x: 800, y: 150 },
  },

  // Skill 4: AV Studio
  {
    id: 'av_editing_studio_agent',
    type: 'agentNode',
    data: {
      label: 'AV Editing Studio',
      agentName: 'av_editing_studio_agent',
      type: 'sequential',
      description: '30s commercial production',
      skill: 'av',
    },
    position: { x: 1200, y: 150 },
  },

  // Skill 5: Focus Group
  {
    id: 'focus_group_evaluator_agent',
    type: 'agentNode',
    data: {
      label: 'Focus Group Evaluator',
      agentName: 'focus_group_evaluator_agent',
      type: 'sequential',
      description: 'Commercial evaluation with simulated focus group',
      skill: 'focus-group',
    },
    position: { x: 1400, y: 150 },
  },

  // Row 2: Sub-agents under their parents
  {
    id: 'combined_research_pipeline',
    type: 'agentNode',
    data: {
      label: 'Combined Research Pipeline',
      agentName: 'combined_research_pipeline',
      type: 'sequential',
      description: 'Sequential research flow',
      skill: 'research',
    },
    position: { x: 400, y: 300 },
  },
  {
    id: 'merge_parallel_insights',
    type: 'agentNode',
    data: {
      label: 'Merge Parallel Insights',
      agentName: 'merge_parallel_insights',
      type: 'parallel',
      description: 'Parallel research coordination',
      skill: 'research',
    },
    position: { x: 200, y: 300 },
  },
  {
    id: 'ad_creative_pipeline',
    type: 'agentNode',
    data: {
      label: 'Ad Creative Pipeline',
      agentName: 'ad_creative_pipeline',
      type: 'sequential',
      description: 'Draft → critique ad copy',
      skill: 'creative',
    },
    position: { x: 700, y: 300 },
  },
  {
    id: 'visual_generation_pipeline',
    type: 'agentNode',
    data: {
      label: 'Visual Generation Pipeline',
      agentName: 'visual_generation_pipeline',
      type: 'sequential',
      description: 'Draft → critique → finalize',
      skill: 'creative',
    },
    position: { x: 900, y: 300 },
  },
  {
    id: 'visual_generator',
    type: 'agentNode',
    data: {
      label: 'Visual Generator',
      agentName: 'visual_generator',
      type: 'tool',
      description: 'Imagen/Veo generation',
      skill: 'creative',
    },
    position: { x: 1100, y: 300 },
  },

  // Ad creative leaf agents
  {
    id: 'ad_copy_drafter',
    type: 'agentNode',
    data: {
      label: 'Ad Copy Drafter',
      agentName: 'ad_copy_drafter',
      type: 'tool',
      description: 'Drafts ad copy',
      skill: 'creative',
    },
    position: { x: 650, y: 450 },
  },
  {
    id: 'ad_copy_critic',
    type: 'agentNode',
    data: {
      label: 'Ad Copy Critic',
      agentName: 'ad_copy_critic',
      type: 'tool',
      description: 'Critiques ad copy',
      skill: 'creative',
    },
    position: { x: 750, y: 450 },
  },
  {
    id: 'visual_concept_drafter',
    type: 'agentNode',
    data: {
      label: 'Visual Concept Drafter',
      agentName: 'visual_concept_drafter',
      type: 'tool',
      description: 'Drafts visual concepts',
      skill: 'creative',
    },
    position: { x: 850, y: 450 },
  },
  {
    id: 'visual_concept_critic',
    type: 'agentNode',
    data: {
      label: 'Visual Concept Critic',
      agentName: 'visual_concept_critic',
      type: 'tool',
      description: 'Critiques visual concepts',
      skill: 'creative',
    },
    position: { x: 950, y: 450 },
  },
  {
    id: 'visual_concept_finalizer',
    type: 'agentNode',
    data: {
      label: 'Visual Concept Finalizer',
      agentName: 'visual_concept_finalizer',
      type: 'tool',
      description: 'Finalizes visual concepts',
      skill: 'creative',
    },
    position: { x: 1050, y: 450 },
  },

  // Row 3: Parallel planners spread wide
  {
    id: 'parallel_planner_agent',
    type: 'agentNode',
    data: {
      label: 'Parallel Planner',
      agentName: 'parallel_planner_agent',
      type: 'parallel',
      description: 'Runs 3 research types simultaneously',
      skill: 'research',
    },
    position: { x: 400, y: 450 },
  },
  {
    id: 'yt_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'YouTube Planner',
      agentName: 'yt_sequential_planner',
      type: 'parallel',
      description: 'YouTube trend analysis',
      skill: 'research',
    },
    position: { x: 200, y: 600 },
  },
  {
    id: 'gs_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'Google Search Planner',
      agentName: 'gs_sequential_planner',
      type: 'parallel',
      description: 'Google Search trend analysis',
      skill: 'research',
    },
    position: { x: 400, y: 600 },
  },
  {
    id: 'ca_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'Campaign Planner',
      agentName: 'ca_sequential_planner',
      type: 'parallel',
      description: 'Campaign research',
      skill: 'research',
    },
    position: { x: 600, y: 600 },
  },

  // Research leaf agents
  {
    id: 'yt_analysis_generator_agent',
    type: 'agentNode',
    data: {
      label: 'YT Analysis Generator',
      agentName: 'yt_analysis_generator_agent',
      type: 'tool',
      description: 'YouTube analysis generation',
      skill: 'research',
    },
    position: { x: 100, y: 750 },
  },
  {
    id: 'yt_web_planner',
    type: 'agentNode',
    data: {
      label: 'YT Web Planner',
      agentName: 'yt_web_planner',
      type: 'tool',
      description: 'YouTube web research planning',
      skill: 'research',
    },
    position: { x: 200, y: 750 },
  },
  {
    id: 'yt_web_searcher',
    type: 'agentNode',
    data: {
      label: 'YT Web Searcher',
      agentName: 'yt_web_searcher',
      type: 'tool',
      description: 'YouTube web searching',
      skill: 'research',
    },
    position: { x: 300, y: 750 },
  },
  {
    id: 'gs_web_planner',
    type: 'agentNode',
    data: {
      label: 'GS Web Planner',
      agentName: 'gs_web_planner',
      type: 'tool',
      description: 'Google Search planning',
      skill: 'research',
    },
    position: { x: 400, y: 750 },
  },
  {
    id: 'gs_web_searcher',
    type: 'agentNode',
    data: {
      label: 'GS Web Searcher',
      agentName: 'gs_web_searcher',
      type: 'tool',
      description: 'Google Search execution',
      skill: 'research',
    },
    position: { x: 500, y: 750 },
  },
  {
    id: 'campaign_web_planner',
    type: 'agentNode',
    data: {
      label: 'Campaign Web Planner',
      agentName: 'campaign_web_planner',
      type: 'tool',
      description: 'Campaign research planning',
      skill: 'research',
    },
    position: { x: 600, y: 750 },
  },
  {
    id: 'campaign_web_searcher',
    type: 'agentNode',
    data: {
      label: 'Campaign Web Searcher',
      agentName: 'campaign_web_searcher',
      type: 'tool',
      description: 'Campaign web searching',
      skill: 'research',
    },
    position: { x: 700, y: 750 },
  },

  // Row 4: Merge planners
  {
    id: 'merge_planners',
    type: 'agentNode',
    data: {
      label: 'Merge Planners',
      agentName: 'merge_planners',
      type: 'tool',
      description: 'Combines research plans',
      skill: 'research',
    },
    position: { x: 400, y: 900 },
  },

  // Row 5-7: Sequential evaluation chain
  {
    id: 'combined_web_evaluator',
    type: 'agentNode',
    data: {
      label: 'Web Evaluator',
      agentName: 'combined_web_evaluator',
      type: 'sequential',
      description: 'Quality checks',
      skill: 'research',
    },
    position: { x: 400, y: 1050 },
  },
  {
    id: 'enhanced_combined_searcher',
    type: 'agentNode',
    data: {
      label: 'Enhanced Searcher',
      agentName: 'enhanced_combined_searcher',
      type: 'sequential',
      description: 'Refines results',
      skill: 'research',
    },
    position: { x: 400, y: 1200 },
  },
  {
    id: 'combined_report_composer',
    type: 'agentNode',
    data: {
      label: 'Report Composer',
      agentName: 'combined_report_composer',
      type: 'sequential',
      description: 'Generates unified report',
      skill: 'research',
    },
    position: { x: 400, y: 1350 },
  },
];

// Define edges (connections between agents)
export const PIPELINE_EDGES: Edge[] = [
  // Root to skill agents
  { id: 'e-root-trends', source: 'root_agent', target: 'trends_and_insights_agent' },
  { id: 'e-root-research', source: 'root_agent', target: 'research_orchestrator' },
  { id: 'e-root-ad', source: 'root_agent', target: 'ad_content_generator_agent' },
  { id: 'e-root-av', source: 'root_agent', target: 'av_editing_studio_agent' },
  { id: 'e-root-focus', source: 'root_agent', target: 'focus_group_evaluator_agent' },

  // Research orchestrator to pipeline
  {
    id: 'e-research-pipeline',
    source: 'research_orchestrator',
    target: 'combined_research_pipeline',
  },

  // Pipeline to merge_parallel_insights
  {
    id: 'e-pipeline-merge-parallel',
    source: 'combined_research_pipeline',
    target: 'merge_parallel_insights',
  },

  // merge_parallel_insights to parallel_planner_agent
  {
    id: 'e-merge-parallel-planner',
    source: 'merge_parallel_insights',
    target: 'parallel_planner_agent',
  },

  // Parallel planner to sequential planners
  {
    id: 'e-planner-yt',
    source: 'parallel_planner_agent',
    target: 'yt_sequential_planner',
  },
  {
    id: 'e-planner-gs',
    source: 'parallel_planner_agent',
    target: 'gs_sequential_planner',
  },
  {
    id: 'e-planner-ca',
    source: 'parallel_planner_agent',
    target: 'ca_sequential_planner',
  },

  // Sequential planners to leaf agents
  { id: 'e-yt-analysis', source: 'yt_sequential_planner', target: 'yt_analysis_generator_agent' },
  { id: 'e-yt-web-plan', source: 'yt_sequential_planner', target: 'yt_web_planner' },
  { id: 'e-yt-web-search', source: 'yt_sequential_planner', target: 'yt_web_searcher' },
  { id: 'e-gs-web-plan', source: 'gs_sequential_planner', target: 'gs_web_planner' },
  { id: 'e-gs-web-search', source: 'gs_sequential_planner', target: 'gs_web_searcher' },
  { id: 'e-ca-web-plan', source: 'ca_sequential_planner', target: 'campaign_web_planner' },
  { id: 'e-ca-web-search', source: 'ca_sequential_planner', target: 'campaign_web_searcher' },

  // merge_parallel_insights to merge_planners
  { id: 'e-merge-parallel-merge', source: 'merge_parallel_insights', target: 'merge_planners' },

  // Sequential flow through research pipeline
  { id: 'e-merge-eval', source: 'merge_planners', target: 'combined_web_evaluator' },
  {
    id: 'e-eval-search',
    source: 'combined_web_evaluator',
    target: 'enhanced_combined_searcher',
  },
  {
    id: 'e-search-report',
    source: 'enhanced_combined_searcher',
    target: 'combined_report_composer',
  },

  // Ad content generator to pipelines
  {
    id: 'e-ad-creative',
    source: 'ad_content_generator_agent',
    target: 'ad_creative_pipeline',
  },
  {
    id: 'e-ad-visual',
    source: 'ad_content_generator_agent',
    target: 'visual_generation_pipeline',
  },
  {
    id: 'e-ad-generator',
    source: 'ad_content_generator_agent',
    target: 'visual_generator',
  },

  // Ad creative pipeline to leaf agents
  { id: 'e-creative-drafter', source: 'ad_creative_pipeline', target: 'ad_copy_drafter' },
  { id: 'e-creative-critic', source: 'ad_creative_pipeline', target: 'ad_copy_critic' },

  // Visual generation pipeline to leaf agents
  { id: 'e-visual-drafter', source: 'visual_generation_pipeline', target: 'visual_concept_drafter' },
  { id: 'e-visual-critic', source: 'visual_generation_pipeline', target: 'visual_concept_critic' },
  { id: 'e-visual-finalizer', source: 'visual_generation_pipeline', target: 'visual_concept_finalizer' },
];
