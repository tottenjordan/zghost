import { useState } from 'react';
import { Blocks, GitBranch, Database } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { ArchitectureDiagram } from './ArchitectureDiagram';
import { MemoryExplorer } from './MemoryExplorer';

interface SkillInfo {
  id: string;
  name: string;
  owner: string;
  description: string;
  version: string;
  tools: string[];
  stateReads: string[];
  stateWrites: string[];
  color: string;
}

const SKILLS: SkillInfo[] = [
  {
    id: 'trend-discovery',
    name: 'Trend Discovery',
    owner: 'Data/Analytics Team',
    description: 'Campaign metadata configuration and real-time trend selection from Google Search and YouTube.',
    version: '1.0.0',
    tools: ['get_google_trends', 'get_yt_trending', 'analyze_trends'],
    stateReads: ['brand', 'target_product', 'target_audience'],
    stateWrites: ['target_search_trends', 'target_yt_trends'],
    color: 'blue',
  },
  {
    id: 'market-research',
    name: 'Market Research',
    owner: 'Research/Content Team',
    description: 'Parallel web research pipeline: YouTube analysis, Google Search insights, and campaign research with citation tracking.',
    version: '1.0.0',
    tools: ['web_search', 'scrape_url', 'evaluate_sources', 'compose_report'],
    stateReads: ['target_search_trends', 'target_yt_trends', 'brand', 'target_product'],
    stateWrites: ['combined_final_cited_report', 'sources', 'url_to_short_id'],
    color: 'green',
  },
  {
    id: 'ad-creative',
    name: 'Ad Creative',
    owner: 'Creative Team',
    description: 'Ad copy drafting with critique loop, visual concept generation with Imagen 4.0 Ultra and Veo 3.1.',
    version: '1.0.0',
    tools: ['generate_image', 'generate_video', 'save_creatives_and_research_report'],
    stateReads: ['combined_final_cited_report', 'brand', 'target_audience', 'key_selling_points'],
    stateWrites: ['final_select_ad_copies', 'final_select_vis_concepts', 'img_artifact_keys', 'vid_artifact_keys'],
    color: 'purple',
  },
  {
    id: 'av-studio',
    name: 'AV Studio',
    owner: 'AV Production Team',
    description: '30-second commercial production with timeline editing, voice synthesis, and music generation.',
    version: '1.0.0',
    tools: ['compose_timeline', 'generate_voiceover', 'generate_music', 'render_commercial'],
    stateReads: ['final_select_ad_copies', 'final_select_vis_concepts', 'vid_artifact_keys'],
    stateWrites: ['commercial_video_url', 'commercial_metadata'],
    color: 'orange',
  },
  {
    id: 'focus-group',
    name: 'Focus Group',
    owner: 'QA/Evaluation Team',
    description: 'Simulated focus group evaluation of generated commercials with multi-criteria rubric scoring.',
    version: '1.0.0',
    tools: ['evaluate_commercial', 'score_rubric', 'generate_feedback'],
    stateReads: ['commercial_video_url', 'commercial_metadata', 'brand', 'target_audience'],
    stateWrites: ['focus_group_results', 'evaluation_scores'],
    color: 'red',
  },
];

const colorMap: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  blue: { bg: 'bg-blue-950/30', border: 'border-blue-800/50', text: 'text-blue-400', badge: 'bg-blue-900/50 text-blue-300 border-blue-700' },
  green: { bg: 'bg-green-950/30', border: 'border-green-800/50', text: 'text-green-400', badge: 'bg-green-900/50 text-green-300 border-green-700' },
  purple: { bg: 'bg-purple-950/30', border: 'border-purple-800/50', text: 'text-purple-400', badge: 'bg-purple-900/50 text-purple-300 border-purple-700' },
  orange: { bg: 'bg-orange-950/30', border: 'border-orange-800/50', text: 'text-orange-400', badge: 'bg-orange-900/50 text-orange-300 border-orange-700' },
  red: { bg: 'bg-red-950/30', border: 'border-red-800/50', text: 'text-red-400', badge: 'bg-red-900/50 text-red-300 border-red-700' },
};

export function SkillsPage() {
  const [highlightedSkill, setHighlightedSkill] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="mb-2 text-3xl font-bold text-zinc-50">Skills Architecture</h1>
        <p className="text-zinc-400">
          Explore the multi-agent skills powering the marketing intelligence pipeline
        </p>
      </div>

      <Tabs defaultValue="skills">
        <TabsList>
          <TabsTrigger value="skills">
            <span className="flex items-center gap-1.5">
              <Blocks className="h-4 w-4" />
              Skills ({SKILLS.length})
            </span>
          </TabsTrigger>
          <TabsTrigger value="architecture">
            <span className="flex items-center gap-1.5">
              <GitBranch className="h-4 w-4" />
              Architecture
            </span>
          </TabsTrigger>
          <TabsTrigger value="memory">
            <span className="flex items-center gap-1.5">
              <Database className="h-4 w-4" />
              Memory Bank
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skills">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {SKILLS.map((skill) => {
              const colors = colorMap[skill.color];
              const isHighlighted = highlightedSkill === skill.id;
              return (
                <Card
                  key={skill.id}
                  className={`cursor-pointer transition-all duration-200 ${
                    isHighlighted ? `ring-2 ring-offset-1 ring-offset-zinc-950 ${colors.border} ${colors.bg}` : 'hover:border-zinc-700'
                  }`}
                  onClick={() => setHighlightedSkill(isHighlighted ? null : skill.id)}
                  data-testid={`skill-card-${skill.id}`}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className={`text-base ${colors.text}`}>{skill.name}</CardTitle>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${colors.badge}`}>
                        v{skill.version}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500">{skill.owner}</p>
                  </CardHeader>
                  <CardContent>
                    <p className="mb-3 text-sm text-zinc-400">{skill.description}</p>

                    <div className="space-y-2">
                      <div>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-600 mb-1">Tools</p>
                        <div className="flex flex-wrap gap-1">
                          {skill.tools.map(tool => (
                            <span key={tool} className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-600 mb-1">Reads</p>
                          {skill.stateReads.map(key => (
                            <p key={key} className="text-[10px] text-zinc-500 truncate">{key}</p>
                          ))}
                        </div>
                        <div>
                          <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-600 mb-1">Writes</p>
                          {skill.stateWrites.map(key => (
                            <p key={key} className="text-[10px] text-zinc-500 truncate">{key}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="architecture">
          <ArchitectureDiagram
            highlightedSkill={highlightedSkill}
            onSelectSkill={(id) => setHighlightedSkill(id === highlightedSkill ? null : id)}
          />
        </TabsContent>

        <TabsContent value="memory">
          <MemoryExplorer />
        </TabsContent>
      </Tabs>
    </div>
  );
}
