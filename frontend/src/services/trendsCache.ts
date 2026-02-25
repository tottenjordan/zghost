import type { SearchTrend, YTTrend } from '../types/trends';
import { api } from './api';
import { parseTrendsFromRunResponse } from '../utils/parseTrends';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';
const TTL_MS = 10 * 60 * 1000; // 10 minutes

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
 * Fetch live trends from the ADK backend, with 10-min TTL cache.
 * Returns cached data if still fresh. Deduplicates concurrent calls.
 */
export async function fetchLiveTrends(force = false): Promise<CachedTrends> {
  if (!force && isCacheValid()) {
    return cache!;
  }

  // Deduplicate concurrent fetches
  if (fetchPromise) {
    return fetchPromise;
  }

  fetchPromise = _doFetch();
  try {
    const result = await fetchPromise;
    return result;
  } finally {
    fetchPromise = null;
  }
}

async function _doFetch(): Promise<CachedTrends> {
  // Create a dedicated session for trend fetching
  const session = await api.createSession(APP_NAME, USER_ID);

  // Send hello to initialize
  await api.sendMessage({
    app_name: APP_NAME,
    user_id: USER_ID,
    session_id: session.session_id,
    message: 'hello',
  });

  // Fetch Google Search trends
  const googleResponse = await api.sendMessage({
    app_name: APP_NAME,
    user_id: USER_ID,
    session_id: session.session_id,
    message: 'select a google trend',
  });

  // Fetch YouTube trends
  const ytResponse = await api.sendMessage({
    app_name: APP_NAME,
    user_id: USER_ID,
    session_id: session.session_id,
    message: 'select a yt trend',
  });

  // Parse responses
  const googleParsed = parseTrendsFromRunResponse(googleResponse);
  const ytParsed = parseTrendsFromRunResponse(ytResponse);

  cache = {
    searchTrends: googleParsed.searchTrends,
    ytTrends: ytParsed.ytTrends,
    fetchedAt: Date.now(),
    sessionId: session.session_id,
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
 */
export function autoSelectFromAvailable(
  available: CachedTrends,
  config: {
    num_search_trends: number;
    num_yt_trends: number;
    strategy: 'top' | 'diverse' | 'relevance';
    campaign?: CampaignContext;
  }
): { searchTrends: SearchTrend[]; ytTrends: YTTrend[]; reasoning: string } {
  const { num_search_trends, num_yt_trends, strategy, campaign } = config;
  let selectedSearch: SearchTrend[];
  let selectedYt: YTTrend[];
  let reasoning: string;

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

  return { searchTrends: selectedSearch, ytTrends: selectedYt, reasoning };
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
