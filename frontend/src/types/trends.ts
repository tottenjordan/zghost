export interface SearchTrend {
  rank: number;
  title: string;
  formattedTraffic: string;
  relatedQueries: string;
  traffic?: string;
  exploreLink?: string;
  image?: {
    newsUrl: string;
    source: string;
    imageUrl: string;
  };
  articles?: Array<{
    title: string;
    timeAgo: string;
    source: string;
    snippet: string;
    url: string;
  }>;
  shareUrl?: string;
}

export interface YTTrend {
  rank: number;
  title: string;
  videoId: string;
  videoUrl: string;
  channelName: string;
  channelUrl: string;
  description: string;
  viewCount: string;
  publishedTime: string;
  thumbnail?: string;
}

export interface TrendSelection {
  target_search_trends: SearchTrend[];
  target_yt_trends: YTTrend[];
}

export interface AutoSelectConfig {
  session_id: string;
  num_search_trends: number;
  num_yt_trends: number;
  strategy?: 'top' | 'diverse' | 'relevance';
}
