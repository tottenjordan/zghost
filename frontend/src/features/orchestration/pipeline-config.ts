import type { Node, Edge } from 'reactflow';

export interface PipelineNodeData {
  label: string;
  agentName: string;
  type: 'orchestrator' | 'sequential' | 'parallel' | 'tool';
  description?: string;
  skill?: 'root' | 'trends' | 'research' | 'creative' | 'av';
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

  // Row 3: Parallel planners spread wide
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
    position: { x: 200, y: 450 },
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
    position: { x: 400, y: 450 },
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
    position: { x: 600, y: 450 },
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
    position: { x: 400, y: 600 },
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
    position: { x: 400, y: 750 },
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
    position: { x: 400, y: 900 },
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
    position: { x: 400, y: 1050 },
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
