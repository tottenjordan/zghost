import { useState } from 'react';
import { Clock, Search, FileText, Code, Globe, ChevronDown, ChevronRight, Image, Video, FileType } from 'lucide-react';
import { ArtifactPlaceholder } from './ArtifactPlaceholder';

interface ProcessedEvent {
  title: string;
  data: any;
}

interface ActivityTimelineProps {
  events: ProcessedEvent[];
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  const getEventIcon = (title: string, eventData?: any) => {
    if (title.includes('Generated Image')) return Image;
    if (title.includes('Generated Video')) return Video;
    if (title.includes('PDF Report')) return FileType;
    if (title.includes('Search') || title.includes('Research')) return Search;
    if (title.includes('Function')) return Code;
    if (title.includes('Sources')) return Globe;
    if (title.includes('Report') || title.includes('Composing')) return FileText;
    return Clock;
  };

  const getEventColor = (title: string) => {
    if (title.includes('Generated Image') || title.includes('Generated Video') || title.includes('PDF Report')) return 'text-pink-400 bg-pink-400/10';
    if (title.includes('Planning')) return 'text-blue-400 bg-blue-400/10';
    if (title.includes('Research') || title.includes('Search')) return 'text-purple-400 bg-purple-400/10';
    if (title.includes('Quality') || title.includes('Evaluating')) return 'text-yellow-400 bg-yellow-400/10';
    if (title.includes('Report') || title.includes('Composing')) return 'text-green-400 bg-green-400/10';
    if (title.includes('Function')) return 'text-orange-400 bg-orange-400/10';
    return 'text-neutral-400 bg-neutral-400/10';
  };

  const toggleEvent = (index: number) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  return (
    <div className="bg-neutral-800/30 border border-neutral-700/50 rounded-lg p-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 text-sm font-medium text-neutral-300 hover:text-neutral-100 transition-colors"
      >
        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <span>Agent Activity ({events.length} events)</span>
      </button>
      
      {isExpanded && (
        <div className="relative mt-3">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-neutral-700"></div>
          <div className="space-y-3">
            {events.map((event, index) => {
              const Icon = getEventIcon(event.title, event.data);
              const colorClass = getEventColor(event.title);
              const isEventExpanded = expandedEvents.has(index);
              const hasDetails = event.data.content || event.data.args || event.data.response || event.data.artifact;
              
              return (
                <div key={index} className="relative flex items-start gap-3">
                  <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center ${colorClass}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 pb-2">
                    <div className="flex items-center gap-2">
                      {hasDetails && (
                        <button
                          onClick={() => toggleEvent(index)}
                          className="p-0.5 hover:bg-neutral-700 rounded transition-colors"
                        >
                          {isEventExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        </button>
                      )}
                      <h4 className="text-sm font-medium text-neutral-200">{event.title}</h4>
                    </div>
                    
                    {isEventExpanded && (
                      <div className="mt-2 ml-5 space-y-2">
                        {event.data.content && (
                          <div className="text-xs text-neutral-400 bg-neutral-900/50 rounded p-2 max-h-40 overflow-y-auto">
                            <pre className="whitespace-pre-wrap font-mono">
                              {typeof event.data.content === 'string' 
                                ? event.data.content 
                                : JSON.stringify(event.data.content, null, 2)}
                            </pre>
                          </div>
                        )}
                        {event.data.args && (
                          <div className="text-xs text-neutral-400 bg-neutral-900/50 rounded p-2 max-h-40 overflow-y-auto">
                            <div className="font-semibold mb-1">Arguments:</div>
                            <pre className="whitespace-pre-wrap font-mono">
                              {JSON.stringify(event.data.args, null, 2)}
                            </pre>
                          </div>
                        )}
                        {event.data.response && (
                          <div className="text-xs text-neutral-400 bg-neutral-900/50 rounded p-2 max-h-40 overflow-y-auto">
                            <div className="font-semibold mb-1">Response:</div>
                            <pre className="whitespace-pre-wrap font-mono">
                              {JSON.stringify(event.data.response, null, 2)}
                            </pre>
                          </div>
                        )}
                        {event.data.artifact && (
                          <div className="text-xs text-neutral-400">
                            <ArtifactPlaceholder
                              artifactKey={event.data.artifact.key}
                              type={event.data.artifact.type}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}