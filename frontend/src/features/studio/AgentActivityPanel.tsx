import { useStreaming } from '../../hooks/useStreaming';
import type { AgentEvent } from '../../types/agents';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Spinner } from '../../components/ui/Spinner';

interface AgentActivityPanelProps {
  sessionId: string | null;
}

const AV_TOOLS = [
  'generate_subject_image',
  'generate_clip_with_frames',
  'extract_frame_from_clip',
  'concatenate_clips',
  'trim_video',
  'save_commercial_artifact',
];

function formatToolName(toolName: string): string {
  return toolName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getActivityDescription(event: AgentEvent): string {
  const toolName = event.data?.tool_name || event.data?.function_name || '';

  switch (toolName) {
    case 'generate_subject_image':
      return `Generating subject image: ${event.data?.args?.subject_name || 'character'}`;
    case 'generate_clip_with_frames':
      return `Generating video clip: ${event.data?.args?.clip_name || 'scene'}`;
    case 'extract_frame_from_clip':
      return `Extracting ${event.data?.args?.frame_position || ''} frame`;
    case 'concatenate_clips':
      return `Concatenating ${event.data?.args?.clip_gcs_uris?.length || 0} clips`;
    case 'trim_video':
      return `Trimming video to ${event.data?.args?.target_duration_seconds || 30}s`;
    case 'save_commercial_artifact':
      return 'Saving final commercial';
    default:
      if (event.type === 'tool_start') {
        return `Running: ${formatToolName(toolName)}`;
      }
      return event.data?.message || 'Processing...';
  }
}

export function AgentActivityPanel({ sessionId }: AgentActivityPanelProps) {
  const streamUrl = sessionId
    ? `${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/stream?session_id=${sessionId}`
    : null;

  const { events, isConnected } = useStreaming(streamUrl);

  const avEvents = events.filter((event) => {
    const toolName = event.data?.tool_name || event.data?.function_name || '';
    return (
      event.agentName === 'av_editing_studio_agent' ||
      AV_TOOLS.includes(toolName)
    );
  });

  const recentEvents = avEvents.slice(-20).reverse();

  const activeOperations = avEvents.filter(
    (event) =>
      event.type === 'tool_start' &&
      !avEvents.some(
        (e) =>
          e.type === 'tool_end' &&
          e.data?.tool_name === event.data?.tool_name &&
          e.timestamp > event.timestamp
      )
  );

  return (
    <Card className="bg-black">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>AV Studio Activity</CardTitle>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                <span className="text-xs text-zinc-400">Live</span>
              </>
            ) : (
              <>
                <div className="h-2 w-2 rounded-full bg-zinc-600" />
                <span className="text-xs text-zinc-500">Offline</span>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Active Operations */}
        {activeOperations.length > 0 && (
          <div className="mb-4">
            <h4 className="mb-2 text-sm font-medium text-zinc-300">
              Active Operations
            </h4>
            <div className="space-y-2">
              {activeOperations.map((event, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 rounded-lg bg-zinc-900 p-3"
                >
                  <Spinner size="sm" className="text-blue-500" />
                  <div className="flex-1">
                    <p className="text-sm text-zinc-100">
                      {getActivityDescription(event)}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Started {new Date(event.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Event Log */}
        <div>
          <h4 className="mb-2 text-sm font-medium text-zinc-300">
            Recent Activity
          </h4>
          {recentEvents.length === 0 ? (
            <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/50">
              <p className="text-sm text-zinc-500">
                {isConnected
                  ? 'Waiting for AV studio activity...'
                  : 'Connect to a session to see activity'}
              </p>
            </div>
          ) : (
            <div className="max-h-96 space-y-1 overflow-y-auto rounded-lg bg-zinc-900 p-2">
              {recentEvents.map((event, idx) => {
                const isError = event.type === 'error';

                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2 border-b border-zinc-800 py-2 text-xs last:border-b-0"
                  >
                    <span className="text-zinc-600">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    <Badge
                      variant={
                        isError
                          ? 'error'
                          : event.type === 'tool_start'
                            ? 'warning'
                            : event.type === 'tool_end'
                              ? 'success'
                              : 'default'
                      }
                      className="shrink-0 text-xs"
                    >
                      {event.type.replace('_', ' ')}
                    </Badge>
                    <span className="flex-1 text-zinc-300">
                      {getActivityDescription(event)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
