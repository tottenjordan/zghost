import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { SearchTrendCard, YTTrendCard } from './TrendCard';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { Session } from '../../types/session';

interface TrendSelectorProps {
  session: Session | null;
  availableSearchTrends?: SearchTrend[];
  availableYtTrends?: YTTrend[];
  selectedSearchTrends: SearchTrend[];
  selectedYtTrends: YTTrend[];
  onToggleSearchTrend: (trend: SearchTrend) => void;
  onToggleYtTrend: (trend: YTTrend) => void;
  onConfirm: () => void;
}

export function TrendSelector({
  session,
  availableSearchTrends: propAvailableSearchTrends,
  availableYtTrends: propAvailableYtTrends,
  selectedSearchTrends,
  selectedYtTrends,
  onToggleSearchTrend,
  onToggleYtTrend,
  onConfirm,
}: TrendSelectorProps) {
  const [searchFilter, setSearchFilter] = useState('');
  const [ytFilter, setYtFilter] = useState('');

  // Use trends from props if available, otherwise fall back to mock data for demo
  const availableSearchTrends: SearchTrend[] = useMemo(() => {
    if (propAvailableSearchTrends && propAvailableSearchTrends.length > 0) {
      return propAvailableSearchTrends;
    }
    return [
      {
        rank: 1,
        title: 'AI Photography Tips',
        formattedTraffic: '500K+',
        relatedQueries: 'ai camera, phone photography, computational photography',
        traffic: '500000',
      },
      {
        rank: 2,
        title: 'Smartphone Camera Comparison 2026',
        formattedTraffic: '200K+',
        relatedQueries: 'best phone camera, pixel vs iphone, camera test',
        traffic: '200000',
      },
      {
        rank: 3,
        title: 'Mobile Video Editing',
        formattedTraffic: '150K+',
        relatedQueries: 'video editor app, phone video quality, 4k mobile',
        traffic: '150000',
      },
      {
        rank: 4,
        title: 'Night Mode Photography',
        formattedTraffic: '100K+',
        relatedQueries: 'low light camera, night photo, astrophotography phone',
        traffic: '100000',
      },
      {
        rank: 5,
        title: 'Sustainable Tech Gadgets',
        formattedTraffic: '80K+',
        relatedQueries: 'eco-friendly phone, recycled materials, green tech',
        traffic: '80000',
      },
    ];
  }, [propAvailableSearchTrends]);

  const availableYtTrends: YTTrend[] = useMemo(() => {
    if (propAvailableYtTrends && propAvailableYtTrends.length > 0) {
      return propAvailableYtTrends;
    }
    return [
      {
        rank: 1,
        title: 'I Tested Every Phone Camera — Here\'s the Winner',
        videoId: 'dQw4w9WgXcQ',
        videoUrl: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
        channelName: 'TechReview Pro',
        channelUrl: 'https://youtube.com/@techreviewpro',
        description: 'Comprehensive camera comparison of the latest flagship phones including low-light, portrait, and video tests.',
        viewCount: '2.4M views',
        publishedTime: '3 days ago',
      },
      {
        rank: 2,
        title: 'AI Features That Changed My Photography',
        videoId: 'abc123def45',
        videoUrl: 'https://youtube.com/watch?v=abc123def45',
        channelName: 'Creative Lens',
        channelUrl: 'https://youtube.com/@creativelens',
        description: 'How AI-powered features like Magic Eraser and Best Take are transforming mobile photography.',
        viewCount: '1.1M views',
        publishedTime: '1 week ago',
      },
      {
        rank: 3,
        title: 'The Future of Mobile Filmmaking',
        videoId: 'xyz789ghi01',
        videoUrl: 'https://youtube.com/watch?v=xyz789ghi01',
        channelName: 'Film Riot',
        channelUrl: 'https://youtube.com/@filmriot',
        description: 'Professional filmmakers use only smartphones to create a short film.',
        viewCount: '890K views',
        publishedTime: '5 days ago',
      },
      {
        rank: 4,
        title: 'Pixel 9 Pro — 30 Days Later Review',
        videoId: 'pqr456stu78',
        videoUrl: 'https://youtube.com/watch?v=pqr456stu78',
        channelName: 'MKBHD',
        channelUrl: 'https://youtube.com/@mkbhd',
        description: 'Long-term review covering battery life, camera performance, and AI features.',
        viewCount: '3.2M views',
        publishedTime: '2 weeks ago',
      },
      {
        rank: 5,
        title: 'Gen Z Marketing Trends You Need to Know',
        videoId: 'lmn012opq34',
        videoUrl: 'https://youtube.com/watch?v=lmn012opq34',
        channelName: 'Marketing Mindset',
        channelUrl: 'https://youtube.com/@marketingmindset',
        description: 'Top marketing strategies targeting Gen Z consumers in the tech space.',
        viewCount: '450K views',
        publishedTime: '4 days ago',
      },
    ];
  }, [propAvailableYtTrends]);

  // Filter trends based on search
  const filteredSearchTrends = useMemo(() => {
    if (!searchFilter) return availableSearchTrends;
    const lower = searchFilter.toLowerCase();
    return availableSearchTrends.filter(
      (trend) =>
        trend.title.toLowerCase().includes(lower) ||
        trend.relatedQueries?.toLowerCase().includes(lower)
    );
  }, [availableSearchTrends, searchFilter]);

  const filteredYtTrends = useMemo(() => {
    if (!ytFilter) return availableYtTrends;
    const lower = ytFilter.toLowerCase();
    return availableYtTrends.filter(
      (trend) =>
        trend.title.toLowerCase().includes(lower) ||
        trend.channelName.toLowerCase().includes(lower) ||
        trend.description.toLowerCase().includes(lower)
    );
  }, [availableYtTrends, ytFilter]);

  const totalSelected = selectedSearchTrends.length + selectedYtTrends.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Select Trends</CardTitle>
          {totalSelected > 0 && (
            <Badge variant="info">
              {totalSelected} selected
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="google">
          <TabsList className="mb-4 w-full">
            <TabsTrigger value="google">
              <span className="flex items-center gap-2">
                Google Search Trends
                {selectedSearchTrends.length > 0 && (
                  <Badge variant="info">
                    {selectedSearchTrends.length}
                  </Badge>
                )}
              </span>
            </TabsTrigger>
            <TabsTrigger value="youtube">
              <span className="flex items-center gap-2">
                YouTube Trends
                {selectedYtTrends.length > 0 && (
                  <Badge variant="info">
                    {selectedYtTrends.length}
                  </Badge>
                )}
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="google">
            <div className="space-y-4">
              <Input
                type="search"
                placeholder="Filter trends..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
              />
              {filteredSearchTrends.length === 0 ? (
                <div className="py-12 text-center text-zinc-500">
                  No Google Search trends available. Start by configuring your campaign
                  and fetching trends.
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {filteredSearchTrends.map((trend) => (
                    <SearchTrendCard
                      key={trend.rank}
                      trend={trend}
                      selected={selectedSearchTrends.some(
                        (t) => t.rank === trend.rank
                      )}
                      onToggle={() => onToggleSearchTrend(trend)}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="youtube">
            <div className="space-y-4">
              <Input
                type="search"
                placeholder="Filter trends..."
                value={ytFilter}
                onChange={(e) => setYtFilter(e.target.value)}
              />
              {filteredYtTrends.length === 0 ? (
                <div className="py-12 text-center text-zinc-500">
                  No YouTube trends available. Start by configuring your campaign and
                  fetching trends.
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {filteredYtTrends.map((trend) => (
                    <YTTrendCard
                      key={trend.rank}
                      trend={trend}
                      selected={selectedYtTrends.some((t) => t.rank === trend.rank)}
                      onToggle={() => onToggleYtTrend(trend)}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {totalSelected > 0 && (
          <div className="mt-6 flex justify-end">
            <Button onClick={onConfirm}>Confirm Selection</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
