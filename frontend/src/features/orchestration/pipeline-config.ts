import type { Node, Edge } from 'reactflow';

export interface PipelineNodeData {
  label: string;
  agentName: string;
  type: 'orchestrator' | 'sequential' | 'parallel' | 'tool';
  description?: string;
}

// Define the agent hierarchy as React Flow nodes
export const PIPELINE_NODES: Node<PipelineNodeData>[] = [
  // Root agent
  {
    id: 'root_agent',
    type: 'agentNode',
    data: {
      label: 'Root Agent',
      agentName: 'root_agent',
      type: 'orchestrator',
      description: 'Main orchestrator',
    },
    position: { x: 400, y: 0 },
  },

  // Skill 1: Trend Discovery
  {
    id: 'trends_and_insights_agent',
    type: 'agentNode',
    data: {
      label: 'Trends & Insights',
      agentName: 'trends_and_insights_agent',
      type: 'sequential',
      description: 'Campaign metadata + trend selection',
    },
    position: { x: 50, y: 120 },
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
    },
    position: { x: 250, y: 120 },
  },
  {
    id: 'combined_research_pipeline',
    type: 'agentNode',
    data: {
      label: 'Combined Research Pipeline',
      agentName: 'combined_research_pipeline',
      type: 'sequential',
      description: 'Sequential research flow',
    },
    position: { x: 250, y: 220 },
  },

  // Parallel research agents
  {
    id: 'yt_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'YouTube Planner',
      agentName: 'yt_sequential_planner',
      type: 'parallel',
      description: 'YouTube trend analysis',
    },
    position: { x: 50, y: 340 },
  },
  {
    id: 'gs_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'Google Search Planner',
      agentName: 'gs_sequential_planner',
      type: 'parallel',
      description: 'Google Search trend analysis',
    },
    position: { x: 250, y: 340 },
  },
  {
    id: 'ca_sequential_planner',
    type: 'agentNode',
    data: {
      label: 'Campaign Planner',
      agentName: 'ca_sequential_planner',
      type: 'parallel',
      description: 'Campaign research',
    },
    position: { x: 450, y: 340 },
  },

  // Merge and evaluation agents
  {
    id: 'merge_planners',
    type: 'agentNode',
    data: {
      label: 'Merge Planners',
      agentName: 'merge_planners',
      type: 'tool',
      description: 'Combines research plans',
    },
    position: { x: 250, y: 460 },
  },
  {
    id: 'combined_web_evaluator',
    type: 'agentNode',
    data: {
      label: 'Web Evaluator',
      agentName: 'combined_web_evaluator',
      type: 'sequential',
      description: 'Quality checks',
    },
    position: { x: 250, y: 560 },
  },
  {
    id: 'enhanced_combined_searcher',
    type: 'agentNode',
    data: {
      label: 'Enhanced Searcher',
      agentName: 'enhanced_combined_searcher',
      type: 'sequential',
      description: 'Refines results',
    },
    position: { x: 250, y: 660 },
  },
  {
    id: 'combined_report_composer',
    type: 'agentNode',
    data: {
      label: 'Report Composer',
      agentName: 'combined_report_composer',
      type: 'sequential',
      description: 'Generates unified report',
    },
    position: { x: 250, y: 760 },
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
    },
    position: { x: 550, y: 120 },
  },
  {
    id: 'ad_creative_pipeline',
    type: 'agentNode',
    data: {
      label: 'Ad Creative Pipeline',
      agentName: 'ad_creative_pipeline',
      type: 'sequential',
      description: 'Draft → critique ad copy',
    },
    position: { x: 500, y: 220 },
  },
  {
    id: 'visual_generation_pipeline',
    type: 'agentNode',
    data: {
      label: 'Visual Generation Pipeline',
      agentName: 'visual_generation_pipeline',
      type: 'sequential',
      description: 'Draft → critique → finalize',
    },
    position: { x: 650, y: 220 },
  },
  {
    id: 'visual_generator',
    type: 'agentNode',
    data: {
      label: 'Visual Generator',
      agentName: 'visual_generator',
      type: 'tool',
      description: 'Imagen/Veo generation',
    },
    position: { x: 800, y: 220 },
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
    },
    position: { x: 750, y: 120 },
  },
];

// Define edges (connections between agents)
export const PIPELINE_EDGES: Edge[] = [
  // Root to skill agents
  { id: 'e-root-trends', source: 'root_agent', target: 'trends_and_insights_agent' },
  { id: 'e-root-research', source: 'root_agent', target: 'research_orchestrator' },
  { id: 'e-root-ad', source: 'root_agent', target: 'ad_content_generator_agent' },
  { id: 'e-root-av', source: 'root_agent', target: 'av_editing_studio_agent' },

  // Research orchestrator to pipeline
  {
    id: 'e-research-pipeline',
    source: 'research_orchestrator',
    target: 'combined_research_pipeline',
  },

  // Pipeline to parallel planners
  {
    id: 'e-pipeline-yt',
    source: 'combined_research_pipeline',
    target: 'yt_sequential_planner',
  },
  {
    id: 'e-pipeline-gs',
    source: 'combined_research_pipeline',
    target: 'gs_sequential_planner',
  },
  {
    id: 'e-pipeline-ca',
    source: 'combined_research_pipeline',
    target: 'ca_sequential_planner',
  },

  // Parallel planners to merge
  { id: 'e-yt-merge', source: 'yt_sequential_planner', target: 'merge_planners' },
  { id: 'e-gs-merge', source: 'gs_sequential_planner', target: 'merge_planners' },
  { id: 'e-ca-merge', source: 'ca_sequential_planner', target: 'merge_planners' },

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
];
