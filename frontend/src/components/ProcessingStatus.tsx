import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

interface ProcessingStatusProps {
  currentAgent?: string;
  isLoading: boolean;
}

// Agent-specific status messages with emojis
const agentStatusMessages: Record<string, string[]> = {
  root_agent: [
    "🎯 Initializing marketing intelligence system...",
    "🧠 Analyzing your request...",
    "🔄 Coordinating specialized agents...",
    "📊 Preparing comprehensive analysis..."
  ],
  campaign_guide_data_generation_agent: [
    "📄 Processing your campaign guide...",
    "🔍 Extracting key marketing insights...",
    "📋 Analyzing brand guidelines...",
    "✨ Understanding target audience..."
  ],
  trends_and_insights_agent: [
    "📈 Analyzing current trends...",
    "🔥 Discovering viral content...",
    "🎯 Matching trends to your brand...",
    "💡 Identifying opportunities..."
  ],
  combined_research_merger: [
    "🔬 Conducting deep research...",
    "🌐 Searching across the web...",
    "📚 Gathering relevant insights...",
    "🔗 Connecting the dots..."
  ],
  combined_research_pipeline: [
    "🔎 Researching trending topics...",
    "📰 Analyzing news and articles...",
    "💬 Understanding audience sentiment...",
    "📊 Compiling research data..."
  ],
  parallel_planner_agent: [
    "🎯 Planning research strategy...",
    "🔀 Coordinating parallel searches...",
    "📝 Organizing research tasks...",
    "⚡ Optimizing search efficiency..."
  ],
  yt_sequential_planner: [
    "📹 Analyzing YouTube trends...",
    "🎬 Finding viral video content...",
    "👁️ Studying viewer engagement...",
    "📺 Discovering content patterns..."
  ],
  gs_sequential_planner: [
    "🔍 Analyzing Google Search trends...",
    "📊 Studying search patterns...",
    "🌟 Finding trending keywords...",
    "💭 Understanding search intent..."
  ],
  ca_sequential_planner: [
    "🎯 Researching campaign strategies...",
    "💼 Analyzing competitor campaigns...",
    "🏆 Finding successful examples...",
    "📈 Identifying best practices..."
  ],
  enhanced_combined_searcher: [
    "🔍 Enhancing search results...",
    "✨ Refining research findings...",
    "🎯 Focusing on key insights...",
    "📊 Validating information..."
  ],
  combined_report_composer: [
    "📝 Composing research report...",
    "🔗 Connecting insights...",
    "✍️ Crafting narrative...",
    "📄 Finalizing documentation..."
  ],
  ad_content_generator_agent: [
    "🎨 Creating ad campaigns...",
    "✍️ Writing compelling copy...",
    "💡 Developing creative concepts...",
    "🎯 Tailoring to your audience..."
  ],
  ad_creative_pipeline: [
    "✍️ Drafting ad copy variations...",
    "🎨 Developing creative angles...",
    "💬 Crafting compelling messages...",
    "✨ Polishing final copy..."
  ],
  visual_generation_pipeline: [
    "🎨 Designing visual concepts...",
    "🖼️ Creating stunning visuals...",
    "🎬 Developing video ideas...",
    "✨ Bringing concepts to life..."
  ],
  visual_generator: [
    "🖼️ Generating images...",
    "🎬 Creating videos...",
    "🎨 Rendering visuals...",
    "✨ Finalizing media assets..."
  ],
  report_generator_agent: [
    "📊 Compiling final report...",
    "📄 Generating PDF document...",
    "🎯 Organizing all findings...",
    "✅ Preparing deliverables..."
  ],
  default: [
    "⚙️ Processing your request...",
    "🔄 Working on it...",
    "💭 Thinking...",
    "⏳ Almost there..."
  ]
};

export function ProcessingStatus({ currentAgent, isLoading }: ProcessingStatusProps) {
  const [messageIndex, setMessageIndex] = useState(0);
  const [dots, setDots] = useState('');

  // Debug logging
  console.log('[ProcessingStatus] Current agent:', currentAgent);

  // Get messages for current agent
  const messages = currentAgent && agentStatusMessages[currentAgent] 
    ? agentStatusMessages[currentAgent] 
    : agentStatusMessages.default;

  // Cycle through messages
  useEffect(() => {
    if (!isLoading) return;

    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 3000); // Change message every 3 seconds

    return () => clearInterval(messageInterval);
  }, [isLoading, messages.length]);

  // Animate dots
  useEffect(() => {
    if (!isLoading) return;

    const dotsInterval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 500);

    return () => clearInterval(dotsInterval);
  }, [isLoading]);

  if (!isLoading) return null;

  return (
    <div className="flex items-center gap-3 text-neutral-300">
      <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
      <p className="text-sm">
        <span className="inline-block min-w-[300px]">
          {messages[messageIndex]}
        </span>
        <span className="inline-block w-[20px] text-neutral-500">{dots}</span>
      </p>
    </div>
  );
}