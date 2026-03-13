#!/usr/bin/env python3
"""Generate Functional Architecture diagram using graphviz."""

import graphviz

dot = graphviz.Digraph('functional_architecture', format='png')
dot.attr(rankdir='TB', bgcolor='#FAFBFC', pad='0.8', nodesep='0.5', ranksep='0.8',
         dpi='150',
         label='Trends & Insights Agent - Functional Architecture\nGoogle ADK Multi-Agent System',
         labelloc='t', fontsize='28', fontname='Helvetica-Bold', fontcolor='#1A237E')
dot.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='13',
         color='#555555', penwidth='1.2', margin='0.25,0.15')
dot.attr('edge', color='#666666', penwidth='1.2', arrowsize='0.8')

# Color scheme
ORCHESTRATOR = '#1A237E'  # dark blue
LLM_AGENT = '#42A5F5'     # light blue
SEQ_AGENT = '#66BB6A'     # green
PAR_AGENT = '#FFAB91'     # orange/peach
TOOL_NODE = '#CE93D8'     # purple (tools)

ORCH_FONT = 'white'
LLM_FONT = '#1A237E'
SEQ_FONT = '#1B5E20'
PAR_FONT = '#BF360C'

def llm_node(name, label):
    dot.node(name, label, fillcolor=LLM_AGENT, fontcolor=LLM_FONT)

def seq_node(name, label):
    dot.node(name, label, fillcolor=SEQ_AGENT, fontcolor=SEQ_FONT)

def par_node(name, label):
    dot.node(name, label, fillcolor=PAR_AGENT, fontcolor=PAR_FONT)

# Root
dot.node('root', 'root_agent\n(Orchestrator)', fillcolor=ORCHESTRATOR, fontcolor='white',
         fontsize='16', penwidth='2.5', width='2.5', height='0.7')

# Top-level agents
llm_node('trends', 'trends_and_insights_agent\n(Trend Discovery)')

# Research Orchestrator
seq_node('research_orch', 'research_orchestrator\n(SequentialAgent)')

# Ad Content Generator
llm_node('ad_gen', 'ad_content_generator_agent\n(Ad Creative)')

# AV Studio & Focus Group
llm_node('av_studio', 'av_editing_studio_agent\n(AV Studio)')
llm_node('focus_group', 'focus_group_evaluator_agent\n(Focus Group)')

# Root edges
dot.edge('root', 'trends')
dot.edge('root', 'research_orch')
dot.edge('root', 'ad_gen')
dot.edge('root', 'av_studio')
dot.edge('root', 'focus_group')

# --- Research Pipeline ---
seq_node('combined_pipeline', 'combined_research_pipeline\n(SequentialAgent)')
llm_node('report_saver', 'report_saver_agent')

dot.edge('research_orch', 'combined_pipeline')
dot.edge('research_orch', 'report_saver')

# Inside combined_research_pipeline
par_node('merge_parallel', 'merge_parallel_insights\n(ParallelAgent)')
llm_node('web_eval', 'combined_web_evaluator')
llm_node('memory_recall', 'memory_recall_agent')
llm_node('enhanced_search', 'enhanced_combined_searcher')
llm_node('report_composer', 'combined_report_composer')

dot.edge('combined_pipeline', 'merge_parallel')
dot.edge('combined_pipeline', 'web_eval')
dot.edge('combined_pipeline', 'memory_recall')
dot.edge('combined_pipeline', 'enhanced_search')
dot.edge('combined_pipeline', 'report_composer')

# Inside merge_parallel_insights
par_node('parallel_planner', 'parallel_planner_agent\n(ParallelAgent)')
llm_node('merge_planners', 'merge_planners')

dot.edge('merge_parallel', 'parallel_planner')
dot.edge('merge_parallel', 'merge_planners')

# Inside parallel_planner_agent
with dot.subgraph() as s:
    s.attr(rank='same')
    llm_node('yt_planner', 'yt_sequential_planner')
    llm_node('gs_planner', 'gs_sequential_planner')
    llm_node('ca_planner', 'ca_sequential_planner')

dot.edge('parallel_planner', 'yt_planner')
dot.edge('parallel_planner', 'gs_planner')
dot.edge('parallel_planner', 'ca_planner')

# --- Ad Content Generator ---
seq_node('ad_creative_pipe', 'ad_creative_pipeline\n(SequentialAgent)')
seq_node('visual_gen_pipe', 'visual_generation_pipeline\n(SequentialAgent)')
llm_node('visual_gen', 'visual_generator')

dot.edge('ad_gen', 'ad_creative_pipe')
dot.edge('ad_gen', 'visual_gen_pipe')
dot.edge('ad_gen', 'visual_gen')

# Ad creative pipeline children
with dot.subgraph() as s:
    s.attr(rank='same')
    llm_node('ad_drafter', 'ad_copy_drafter')
    llm_node('ad_critic', 'ad_copy_critic')
    llm_node('ad_finalizer', 'ad_copy_finalizer')

dot.edge('ad_creative_pipe', 'ad_drafter')
dot.edge('ad_creative_pipe', 'ad_critic')
dot.edge('ad_creative_pipe', 'ad_finalizer')

# Visual generation pipeline children
with dot.subgraph() as s:
    s.attr(rank='same')
    llm_node('vis_drafter', 'visual_concept_drafter')
    llm_node('vis_critic', 'visual_concept_critic')
    llm_node('vis_finalizer', 'visual_concept_finalizer')

dot.edge('visual_gen_pipe', 'vis_drafter')
dot.edge('visual_gen_pipe', 'vis_critic')
dot.edge('visual_gen_pipe', 'vis_finalizer')

# Legend
with dot.subgraph(name='cluster_legend') as legend:
    legend.attr(label='Legend', fontsize='14', fontname='Helvetica-Bold',
                style='rounded', color='#CCCCCC', bgcolor='#FFFFFF')
    legend.node('leg_llm', 'LlmAgent', fillcolor=LLM_AGENT, fontcolor=LLM_FONT, fontsize='11')
    legend.node('leg_seq', 'SequentialAgent', fillcolor=SEQ_AGENT, fontcolor=SEQ_FONT, fontsize='11')
    legend.node('leg_par', 'ParallelAgent', fillcolor=PAR_AGENT, fontcolor=PAR_FONT, fontsize='11')
    legend.node('leg_orch', 'Orchestrator', fillcolor=ORCHESTRATOR, fontcolor='white', fontsize='11')
    # invisible edges for layout
    legend.edge('leg_orch', 'leg_llm', style='invis')
    legend.edge('leg_llm', 'leg_seq', style='invis')
    legend.edge('leg_seq', 'leg_par', style='invis')

# Render
dot.render('/usr/local/google/home/jwortz/zghost/functional_architecture_diagram',
           cleanup=True)
print("Functional architecture diagram saved successfully.")
