import { useNavigate } from 'react-router-dom';
import { useCampaignStore } from '../../stores/campaignStore';
import { cn } from '../../lib/utils';

export function SessionBreadcrumb() {
  const navigate = useNavigate();
  const { config, selectedSearchTrends, selectedYtTrends, activeRubrics, pipelineStatus } = useCampaignStore();

  const totalTrends = selectedSearchTrends.length + selectedYtTrends.length;
  const brandName = config.brand || config.target_product;

  const chips = [
    {
      label: brandName || 'No brand',
      color: brandName ? 'green' : 'amber',
      onClick: () => navigate('/trends'),
    },
    {
      label: totalTrends > 0 ? `${totalTrends} trend${totalTrends !== 1 ? 's' : ''}` : 'No trends',
      color: totalTrends > 0 ? 'green' : 'amber',
      onClick: () => navigate('/trends'),
    },
    {
      label: activeRubrics.length > 0 ? `${activeRubrics.length} rubric${activeRubrics.length !== 1 ? 's' : ''}` : 'Default rubric',
      color: activeRubrics.length > 0 ? 'green' : 'gray',
      onClick: () => navigate('/rating'),
    },
    {
      label: pipelineStatus.charAt(0).toUpperCase() + pipelineStatus.slice(1),
      color:
        pipelineStatus === 'idle' ? 'gray' :
        pipelineStatus === 'running' ? 'blue' :
        pipelineStatus === 'completed' ? 'green' :
        'red',
      onClick: () => navigate('/orchestration'),
      pulse: pipelineStatus === 'running',
    },
  ];

  return (
    <div className="h-8 flex items-center gap-2 px-4 bg-zinc-900/80 border-b border-zinc-800/60">
      {chips.map((chip, idx) => (
        <button
          key={idx}
          onClick={chip.onClick}
          className={cn(
            'px-2 py-0.5 rounded-md text-xs font-medium transition-all hover:ring-1 hover:ring-zinc-700',
            chip.color === 'green' && 'bg-green-600/20 text-green-400 border border-green-600/30',
            chip.color === 'amber' && 'bg-amber-600/20 text-amber-400 border border-amber-600/30',
            chip.color === 'gray' && 'bg-zinc-800/50 text-zinc-400 border border-zinc-700/50',
            chip.color === 'blue' && 'bg-blue-600/20 text-blue-400 border border-blue-600/30',
            chip.color === 'red' && 'bg-red-600/20 text-red-400 border border-red-600/30',
            chip.pulse && 'animate-pulse'
          )}
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}
