import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';

interface ArchitectureDiagramProps {
  highlightedSkill: string | null;
  onSelectSkill: (id: string) => void;
}

interface Node {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  skillId?: string;
  isSubAgent?: boolean;
}

const colorMap: Record<string, { fill: string; stroke: string; text: string }> = {
  root: { fill: '#27272a', stroke: '#52525b', text: '#e4e4e7' },
  blue: { fill: '#1e3a8a', stroke: '#3b82f6', text: '#93c5fd' },
  green: { fill: '#14532d', stroke: '#22c55e', text: '#86efac' },
  purple: { fill: '#581c87', stroke: '#a855f7', text: '#d8b4fe' },
  orange: { fill: '#7c2d12', stroke: '#f97316', text: '#fdba74' },
  red: { fill: '#7f1d1d', stroke: '#ef4444', text: '#fca5a5' },
};

export function ArchitectureDiagram({ highlightedSkill, onSelectSkill }: ArchitectureDiagramProps) {
  const nodes: Node[] = [
    // Root
    { id: 'root', label: 'root_agent', x: 400, y: 50, width: 140, height: 50, color: 'root' },

    // Main skills
    { id: 'trend-discovery', label: 'trends_and_insights', x: 100, y: 180, width: 150, height: 50, color: 'blue', skillId: 'trend-discovery' },
    { id: 'market-research', label: 'research_orchestrator', x: 280, y: 180, width: 160, height: 50, color: 'green', skillId: 'market-research' },
    { id: 'ad-creative', label: 'ad_content_generator', x: 470, y: 180, width: 160, height: 50, color: 'purple', skillId: 'ad-creative' },
    { id: 'av-studio', label: 'av_editing_studio', x: 660, y: 180, width: 150, height: 50, color: 'orange', skillId: 'av-studio' },
    { id: 'focus-group', label: 'focus_group_evaluator', x: 840, y: 180, width: 160, height: 50, color: 'red', skillId: 'focus-group' },

    // Market research sub-agents
    { id: 'mr-pipeline', label: 'combined_research_pipeline', x: 280, y: 280, width: 160, height: 40, color: 'green', isSubAgent: true },
    { id: 'mr-yt', label: 'yt_sequential_planner', x: 150, y: 370, width: 140, height: 35, color: 'green', isSubAgent: true },
    { id: 'mr-gs', label: 'gs_sequential_planner', x: 310, y: 370, width: 140, height: 35, color: 'green', isSubAgent: true },
    { id: 'mr-ca', label: 'ca_sequential_planner', x: 470, y: 370, width: 140, height: 35, color: 'green', isSubAgent: true },

    // Ad creative sub-agents
    { id: 'ac-copy', label: 'ad_creative_pipeline', x: 400, y: 280, width: 140, height: 35, color: 'purple', isSubAgent: true },
    { id: 'ac-visual', label: 'visual_generation_pipeline', x: 560, y: 280, width: 170, height: 35, color: 'purple', isSubAgent: true },
    { id: 'ac-gen', label: 'visual_generator', x: 560, y: 330, width: 120, height: 35, color: 'purple', isSubAgent: true },
  ];

  const edges = [
    // Root to main skills
    { from: 'root', to: 'trend-discovery' },
    { from: 'root', to: 'market-research' },
    { from: 'root', to: 'ad-creative' },
    { from: 'root', to: 'av-studio' },
    { from: 'root', to: 'focus-group' },

    // Market research hierarchy
    { from: 'market-research', to: 'mr-pipeline' },
    { from: 'mr-pipeline', to: 'mr-yt' },
    { from: 'mr-pipeline', to: 'mr-gs' },
    { from: 'mr-pipeline', to: 'mr-ca' },

    // Ad creative hierarchy
    { from: 'ad-creative', to: 'ac-copy' },
    { from: 'ad-creative', to: 'ac-visual' },
    { from: 'ac-visual', to: 'ac-gen' },
  ];

  const getNode = (id: string) => nodes.find(n => n.id === id)!;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Agent Architecture Diagram
        </CardTitle>
        <p className="text-xs text-zinc-500">
          Click on skill nodes to highlight them
        </p>
      </CardHeader>
      <CardContent>
        <svg viewBox="0 0 1050 450" className="w-full h-auto" style={{ maxHeight: '600px' }}>
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
            >
              <polygon points="0 0, 8 4, 0 8" fill="#52525b" />
            </marker>
          </defs>

          {/* Edges */}
          <g>
            {edges.map(({ from, to }, i) => {
              const fromNode = getNode(from);
              const toNode = getNode(to);
              const x1 = fromNode.x + fromNode.width / 2;
              const y1 = fromNode.y + fromNode.height;
              const x2 = toNode.x + toNode.width / 2;
              const y2 = toNode.y;

              return (
                <line
                  key={i}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#52525b"
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                />
              );
            })}
          </g>

          {/* Nodes */}
          <g>
            {nodes.map((node) => {
              const colors = colorMap[node.color];
              const isHighlighted = node.skillId && highlightedSkill === node.skillId;
              const isClickable = !!node.skillId && !node.isSubAgent;

              return (
                <g
                  key={node.id}
                  onClick={() => {
                    if (isClickable) {
                      onSelectSkill(node.skillId!);
                    }
                  }}
                  className={isClickable ? 'cursor-pointer' : ''}
                  style={{ transition: 'all 0.2s' }}
                >
                  <rect
                    x={node.x}
                    y={node.y}
                    width={node.width}
                    height={node.height}
                    rx="8"
                    fill={colors.fill}
                    stroke={isHighlighted ? colors.stroke : '#52525b'}
                    strokeWidth={isHighlighted ? '3' : node.isSubAgent ? '1' : '2'}
                    opacity={node.isSubAgent ? 0.7 : 1}
                  />
                  <text
                    x={node.x + node.width / 2}
                    y={node.y + node.height / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={colors.text}
                    fontSize={node.isSubAgent ? '10' : '12'}
                    fontWeight={node.isSubAgent ? 'normal' : '600'}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-zinc-500" style={{ backgroundColor: colorMap.root.fill }} />
            <span className="text-zinc-500">Orchestrator</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-blue-600" style={{ backgroundColor: colorMap.blue.fill }} />
            <span className="text-zinc-500">Trend Discovery</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-green-600" style={{ backgroundColor: colorMap.green.fill }} />
            <span className="text-zinc-500">Market Research</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-purple-600" style={{ backgroundColor: colorMap.purple.fill }} />
            <span className="text-zinc-500">Ad Creative</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-orange-600" style={{ backgroundColor: colorMap.orange.fill }} />
            <span className="text-zinc-500">AV Studio</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded border-2 border-red-600" style={{ backgroundColor: colorMap.red.fill }} />
            <span className="text-zinc-500">Focus Group</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
