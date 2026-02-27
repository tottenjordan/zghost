import type { SearchTrend, YTTrend } from '../types/trends';
import { evaluateBrandSafety, type BrandSafetyResult } from './brandSafety';

const API_BASE = import.meta.env.VITE_API_BASE || '';
const TTL_MS = 10 * 60 * 1000; // 10-minute client-side TTL (server has 1-hour cache)

interface CachedTrends {
  searchTrends: SearchTrend[];
  ytTrends: YTTrend[];
  fetchedAt: number;
  sessionId: string;
}

let cache: CachedTrends | null = null;
let fetchPromise: Promise<CachedTrends> | null = null;

function isCacheValid(): boolean {
  return cache !== null && Date.now() - cache.fetchedAt < TTL_MS;
}

/**
 * Fetch live trends from the api_server, with 10-min client-side TTL cache.
 * The server caches for 1 hour, so rapid refreshes are cheap.
 */
export async function fetchLiveTrends(force = false): Promise<CachedTrends> {
  if (!force && isCacheValid()) {
    return cache!;
  }

  // Deduplicate concurrent fetches
  if (fetchPromise) {
    return fetchPromise;
  }

  fetchPromise = _doFetch(force);
  try {
    const result = await fetchPromise;
    return result;
  } finally {
    fetchPromise = null;
  }
}

async function _doFetch(forceRefresh = false): Promise<CachedTrends> {
  const params = forceRefresh ? '?force_refresh=true' : '';
  const response = await fetch(`${API_BASE}/api/v1/trends/available${params}`);

  if (!response.ok) {
    throw new Error(
      `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
    );
  }

  const data = await response.json();

  // Map server TrendInfo objects to frontend SearchTrend/YTTrend types
  const searchTrends: SearchTrend[] = (data.search_trends || []).map(
    (t: any, index: number) => ({
      rank: t.metadata?.rank ?? index + 1,
      title: t.title,
      formattedTraffic: 'N/A',
      relatedQueries: '',
    })
  );

  const ytTrends: YTTrend[] = (data.youtube_trends || []).map(
    (t: any, index: number) => ({
      rank: t.metadata?.rank ?? index + 1,
      title: t.title,
      videoId: t.metadata?.videoId || t.trend_id?.replace('yt-', '') || '',
      videoUrl: t.metadata?.videoUrl || '',
      channelName: t.metadata?.channelName || 'Unknown',
      channelUrl: '',
      description: '',
      viewCount: 'N/A',
      publishedTime: 'N/A',
    })
  );

  cache = {
    searchTrends,
    ytTrends,
    fetchedAt: Date.now(),
    sessionId: '',
  };

  return cache;
}

/** Get cached trends without fetching. Returns null if cache empty or expired. */
export function getCachedTrends(): CachedTrends | null {
  return isCacheValid() ? cache : null;
}

/** Invalidate the cache (e.g. when campaign config changes) */
export function invalidateTrendsCache(): void {
  cache = null;
}

export interface CampaignContext {
  brand: string;
  target_product: string;
  target_audience: string;
  key_selling_points: string;
}

/**
 * Auto-select trends from the available set using a local strategy.
 * When campaign context is provided with 'relevance' strategy, trends are
 * scored by keyword overlap with brand, product, audience, and selling points.
 * Brand safety filtering is applied to remove unsafe trends (score < 5).
 */
export function autoSelectFromAvailable(
  available: CachedTrends,
  config: {
    num_search_trends: number;
    num_yt_trends: number;
    strategy: 'top' | 'diverse' | 'relevance';
    campaign?: CampaignContext;
  }
): { searchTrends: SearchTrend[]; ytTrends: YTTrend[]; reasoning: string; safetyResult?: BrandSafetyResult } {
  const { num_search_trends, num_yt_trends, strategy, campaign } = config;
  let selectedSearch: SearchTrend[];
  let selectedYt: YTTrend[];
  let reasoning: string;
  const brand = campaign?.brand || campaign?.target_product || '';

  switch (strategy) {
    case 'top':
      selectedSearch = [...available.searchTrends]
        .sort((a, b) => a.rank - b.rank)
        .slice(0, num_search_trends);
      selectedYt = [...available.ytTrends]
        .sort((a, b) => a.rank - b.rank)
        .slice(0, num_yt_trends);
      reasoning = `Selected top ${num_search_trends} Google and top ${num_yt_trends} YouTube trends by rank.`;
      break;

    case 'diverse':
      selectedSearch = pickEveryNth(available.searchTrends, num_search_trends);
      selectedYt = pickEveryNth(available.ytTrends, num_yt_trends);
      reasoning = `Selected ${num_search_trends} diverse Google and ${num_yt_trends} diverse YouTube trends spread across rankings for topic variety.`;
      break;

    case 'relevance':
    default: {
      const keywords = buildKeywords(campaign);

      if (keywords.length === 0) {
        // No campaign context — fall back to top-ranked
        selectedSearch = [...available.searchTrends]
          .sort((a, b) => a.rank - b.rank)
          .slice(0, num_search_trends);
        selectedYt = [...available.ytTrends]
          .sort((a, b) => a.rank - b.rank)
          .slice(0, num_yt_trends);
        reasoning = `No campaign context set — selected top ${num_search_trends} Google and top ${num_yt_trends} YouTube trends by rank. Set brand/product for smarter selection.`;
        break;
      }

      // Score search trends by relevance to campaign
      const scoredSearch = available.searchTrends.map((t) => ({
        trend: t,
        score: scoreSearchTrend(t, keywords),
      }));
      scoredSearch.sort((a, b) => b.score - a.score || a.trend.rank - b.trend.rank);
      selectedSearch = scoredSearch.slice(0, num_search_trends).map((s) => s.trend);

      // Score YT trends by relevance to campaign
      const scoredYt = available.ytTrends.map((t) => ({
        trend: t,
        score: scoreYtTrend(t, keywords),
      }));
      scoredYt.sort((a, b) => b.score - a.score || a.trend.rank - b.trend.rank);
      selectedYt = scoredYt.slice(0, num_yt_trends).map((s) => s.trend);

      const brandLabel = campaign?.brand || campaign?.target_product || 'campaign';
      const topSearchMatch = selectedSearch[0]?.title || 'N/A';
      const topYtMatch = selectedYt[0]?.title || 'N/A';
      reasoning = `Ranked by relevance to "${brandLabel}". Top Google match: "${topSearchMatch}". Top YouTube match: "${topYtMatch}". Keywords used: ${keywords.slice(0, 8).join(', ')}.`;
      break;
    }
  }

  // Apply brand safety filtering
  const safetyResult = evaluateBrandSafety(selectedSearch, selectedYt, brand);

  // Filter out unsafe trends (score < 5)
  const safeSearchTrends = selectedSearch.filter((trend) => {
    const score = safetyResult.searchTrendScores.find(
      (s) => s.trendTitle === trend.title
    );
    return !score || score.score >= 5;
  });

  const safeYtTrends = selectedYt.filter((trend) => {
    const score = safetyResult.ytTrendScores.find(
      (s) => s.trendTitle === trend.title
    );
    return !score || score.score >= 5;
  });

  // Count filtered trends
  const filteredSearchCount = selectedSearch.length - safeSearchTrends.length;
  const filteredYtCount = selectedYt.length - safeYtTrends.length;

  // Update reasoning if trends were filtered
  if (filteredSearchCount > 0 || filteredYtCount > 0) {
    const filterNote = ` Brand safety filter removed ${filteredSearchCount} Google and ${filteredYtCount} YouTube trends due to unsafe content.`;
    reasoning += filterNote;
  }

  return {
    searchTrends: safeSearchTrends,
    ytTrends: safeYtTrends,
    reasoning,
    safetyResult,
  };
}

/** Extract scoring keywords from campaign context */
function buildKeywords(campaign?: CampaignContext): string[] {
  if (!campaign) return [];
  const text = [
    campaign.brand,
    campaign.target_product,
    campaign.target_audience,
    campaign.key_selling_points,
  ]
    .filter(Boolean)
    .join(' ');

  if (!text.trim()) return [];

  // Split into individual words, lowercase, deduplicate, drop stopwords
  const stopwords = new Set([
    'the', 'a', 'an', 'and', 'or', 'for', 'in', 'on', 'at', 'to', 'of',
    'is', 'it', 'its', 'with', 'by', 'as', 'from', 'that', 'this', 'be',
    'are', 'was', 'were', 'has', 'have', 'had', 'but', 'not', 'no', 'so',
    'if', 'we', 'our', 'you', 'your', 'they', 'their', 'e.g.', 'etc',
    'including', 'such', 'also', 'about', '-',
  ]);

  const words = text
    .toLowerCase()
    .replace(/[,;.!?()]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 1 && !stopwords.has(w));

  return [...new Set(words)];
}

/** Score a search trend against campaign keywords (0-100) */
function scoreSearchTrend(trend: SearchTrend, keywords: string[]): number {
  const text = [trend.title, trend.relatedQueries || ''].join(' ').toLowerCase();
  let hits = 0;
  for (const kw of keywords) {
    if (text.includes(kw)) hits++;
  }
  // Normalize: each keyword match adds weight, rank is tiebreaker
  return (hits / keywords.length) * 100;
}

/** Score a YT trend against campaign keywords (0-100) */
function scoreYtTrend(trend: YTTrend, keywords: string[]): number {
  const text = [trend.title, trend.description, trend.channelName]
    .join(' ')
    .toLowerCase();
  let hits = 0;
  for (const kw of keywords) {
    if (text.includes(kw)) hits++;
  }
  return (hits / keywords.length) * 100;
}

function pickEveryNth<T>(items: T[], count: number): T[] {
  if (items.length <= count) return [...items];
  const step = items.length / count;
  const result: T[] = [];
  for (let i = 0; i < count; i++) {
    result.push(items[Math.floor(i * step)]);
  }
  return result;
}
