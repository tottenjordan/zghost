import { TrendingUp, Youtube, Check } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { useEffect, useState, useRef } from 'react';

interface TrendSelectorProps {
  googleTrends: any[];
  youtubeTrends: any[];
  onSelect: (type: 'google' | 'youtube', trend: any) => void;
  isLoading: boolean;
  selectedGoogleTrend?: string | null;
  selectedYoutubeTrend?: string | null;
}

export function TrendSelector({ 
  googleTrends, 
  youtubeTrends, 
  onSelect, 
  isLoading,
  selectedGoogleTrend,
  selectedYoutubeTrend 
}: TrendSelectorProps) {
  const [activeTab, setActiveTab] = useState('google');
  const youtubeTabRef = useRef<HTMLDivElement>(null);
  const trendSelectorRef = useRef<HTMLDivElement>(null);
  
  // Auto-switch to YouTube tab when YouTube trends are populated and Google trend is selected
  useEffect(() => {
    if (youtubeTrends.length > 0 && selectedGoogleTrend && !selectedYoutubeTrend) {
      setActiveTab('youtube');
      
      // Scroll to the top of the trend selector and focus on YouTube content
      setTimeout(() => {
        if (trendSelectorRef.current) {
          trendSelectorRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        if (youtubeTabRef.current) {
          const firstCard = youtubeTabRef.current.querySelector('.cursor-pointer');
          if (firstCard) {
            (firstCard as HTMLElement).focus();
          }
        }
      }, 100);
    }
  }, [youtubeTrends.length, selectedGoogleTrend, selectedYoutubeTrend]);
  
  // If both trends are selected, show only the selected ones
  const bothSelected = selectedGoogleTrend && selectedYoutubeTrend;
  
  if (bothSelected) {
    const selectedGoogle = googleTrends.find(t => t.name === selectedGoogleTrend);
    const selectedYT = youtubeTrends.find(t => t.title === selectedYoutubeTrend);
    
    return (
      <Card className="p-6 bg-neutral-800/50 border-neutral-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Check className="h-5 w-5 text-green-400" />
          Selected Trends
        </h3>
        
        <div className="space-y-3">
          {selectedGoogle && (
            <Card className="p-4 bg-green-900/30 border-green-600">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-400" />
                <span className="font-medium text-white">Google Trend:</span>
                <span className="text-white">{selectedGoogle.name}</span>
              </div>
            </Card>
          )}
          
          {selectedYT && (
            <Card className="p-4 bg-red-900/30 border-red-600">
              <div className="flex items-center gap-2">
                <Youtube className="h-4 w-4 text-red-400" />
                <span className="font-medium text-white">YouTube Trend:</span>
                <span className="text-white">{selectedYT.title}</span>
              </div>
            </Card>
          )}
        </div>
      </Card>
    );
  }
  
  return (
    <Card ref={trendSelectorRef} className="p-6 bg-neutral-800/50 border-neutral-700">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-blue-400" />
        Select a Trend to Analyze
      </h3>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 bg-neutral-900/50">
          <TabsTrigger value="google" className="data-[state=active]:bg-neutral-700">
            Google Trends ({googleTrends.length})
          </TabsTrigger>
          <TabsTrigger value="youtube" className="data-[state=active]:bg-neutral-700">
            YouTube Trends ({youtubeTrends.length})
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="google" className="mt-4 space-y-3">
          {googleTrends.length > 0 ? (
            googleTrends.map((trend, index) => {
              const isSelected = selectedGoogleTrend === trend.name;
              return (
                <Card 
                  key={index} 
                  className={`p-4 border transition-colors cursor-pointer ${
                    isSelected 
                      ? 'bg-green-900/30 border-green-600' 
                      : 'bg-neutral-900/50 border-neutral-700 hover:border-neutral-600'
                  }`}
                  onClick={() => !isLoading && !isSelected && onSelect('google', trend)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      if (!isLoading && !isSelected) onSelect('google', trend);
                    }
                  }}
                  tabIndex={0}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-white flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-green-400" />
                        {trend.name || trend.title}
                        {isSelected && (
                          <Check className="h-4 w-4 text-green-400 ml-auto" />
                        )}
                      </h4>
                      {trend.description && (
                        <p className="text-sm text-neutral-400 mt-1">{trend.description}</p>
                      )}
                      {trend.traffic && (
                        <p className="text-xs text-neutral-500 mt-2">
                          Traffic: {trend.traffic}
                        </p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!isSelected) onSelect('google', trend);
                      }}
                      disabled={isLoading || isSelected}
                      className={isSelected ? "bg-green-600 cursor-default" : "bg-blue-600 hover:bg-blue-700"}
                    >
                      {isSelected ? (
                        <>
                          <Check className="h-3 w-3 mr-1" />
                          Selected
                        </>
                      ) : (
                        'Select'
                      )}
                    </Button>
                  </div>
                </Card>
              );
            })
          ) : (
            <p className="text-neutral-400 text-center py-4">No Google trends available</p>
          )}
        </TabsContent>
        
        <TabsContent ref={youtubeTabRef} value="youtube" className="mt-4 space-y-3">
          {youtubeTrends.length > 0 ? (
            youtubeTrends.map((trend, index) => {
              const isSelected = selectedYoutubeTrend === trend.title;
              return (
                <Card 
                  key={index} 
                  className={`p-4 border transition-colors cursor-pointer ${
                    isSelected 
                      ? 'bg-red-900/30 border-red-600' 
                      : 'bg-neutral-900/50 border-neutral-700 hover:border-neutral-600'
                  }`}
                  onClick={() => !isLoading && !isSelected && onSelect('youtube', trend)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      if (!isLoading && !isSelected) onSelect('youtube', trend);
                    }
                  }}
                  tabIndex={0}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-white flex items-center gap-2">
                        <Youtube className="h-4 w-4 text-red-400" />
                        {trend.title}
                        {isSelected && (
                          <Check className="h-4 w-4 text-green-400 ml-auto" />
                        )}
                      </h4>
                      {trend.description && (
                        <p className="text-sm text-neutral-400 mt-1">{trend.description}</p>
                      )}
                      {trend.channel && (
                        <p className="text-xs text-neutral-500 mt-2">
                          Channel: {trend.channel}
                        </p>
                      )}
                      {trend.views && (
                        <p className="text-xs text-neutral-500">
                          Views: {trend.views}
                        </p>
                      )}
                      {trend.duration && (
                        <p className="text-xs text-neutral-500">
                          Duration: {trend.duration}
                        </p>
                      )}
                      {trend.url && (
                        <a 
                          href={trend.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-blue-400 hover:text-blue-300 mt-1 inline-block"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Watch on YouTube →
                        </a>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!isSelected) onSelect('youtube', trend);
                      }}
                      disabled={isLoading || isSelected}
                      className={isSelected ? "bg-green-600 cursor-default" : "bg-blue-600 hover:bg-blue-700"}
                    >
                      {isSelected ? (
                        <>
                          <Check className="h-3 w-3 mr-1" />
                          Selected
                        </>
                      ) : (
                        'Select'
                      )}
                    </Button>
                  </div>
                </Card>
              );
            })
          ) : (
            <p className="text-neutral-400 text-center py-4">No YouTube trends available</p>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  );
}