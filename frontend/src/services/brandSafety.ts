import type { SearchTrend, YTTrend } from '../types/trends';

export interface BrandSafetyScore {
  trendTitle: string;
  score: number; // 1-10
  level: 'safe' | 'caution' | 'unsafe';
  reasoning: string;
}

export interface BrandSafetyResult {
  searchTrendScores: BrandSafetyScore[];
  ytTrendScores: BrandSafetyScore[];
}

// Unsafe categories with keywords and severity
const UNSAFE_KEYWORDS = {
  violence: {
    keywords: ['shooting', 'murder', 'attack', 'killed', 'dead', 'bomb', 'terror', 'war', 'weapon', 'gun', 'death', 'massacre'],
    severity: 3,
  },
  politics: {
    keywords: ['impeach', 'scandal', 'protest', 'riot', 'controversy', 'election fraud', 'coup', 'corruption'],
    severity: 2,
  },
  adult: {
    keywords: ['explicit', 'nude', 'adult', 'pornographic', 'nsfw', 'sex'],
    severity: 3,
  },
  disaster: {
    keywords: ['earthquake', 'tsunami', 'flood', 'hurricane', 'wildfire', 'crash', 'collapse', 'disaster', 'tragedy'],
    severity: 2,
  },
  health_crisis: {
    keywords: ['pandemic', 'outbreak', 'disease', 'virus', 'epidemic', 'infection'],
    severity: 2,
  },
  crime: {
    keywords: ['arrested', 'fraud', 'scam', 'theft', 'robbery', 'assault', 'abuse', 'kidnap'],
    severity: 2,
  },
  hate: {
    keywords: ['racist', 'hate crime', 'discrimination', 'supremacist', 'extremist'],
    severity: 3,
  },
};

/**
 * Evaluates brand safety for a list of trends using client-side heuristic scoring.
 *
 * Scoring logic:
 * - Start at 10 (fully safe)
 * - Each unsafe keyword match reduces score by its category severity (2-3 points)
 * - Minimum score is 1
 * - Level: 8-10 = "safe", 5-7 = "caution", 1-4 = "unsafe"
 */
export function evaluateBrandSafety(
  searchTrends: SearchTrend[],
  ytTrends: YTTrend[],
  brand: string
): BrandSafetyResult {
  const searchTrendScores = searchTrends.map((trend) =>
    scoreSearchTrend(trend, brand)
  );
  const ytTrendScores = ytTrends.map((trend) => scoreYtTrend(trend, brand));

  return {
    searchTrendScores,
    ytTrendScores,
  };
}

function scoreSearchTrend(trend: SearchTrend, brand: string): BrandSafetyScore {
  const text = [
    trend.title,
    trend.relatedQueries || '',
    ...(trend.articles?.map((a) => a.title + ' ' + a.snippet) || []),
  ]
    .join(' ')
    .toLowerCase();

  return calculateSafetyScore(trend.title, text, brand);
}

function scoreYtTrend(trend: YTTrend, brand: string): BrandSafetyScore {
  const text = [trend.title, trend.description, trend.channelName]
    .join(' ')
    .toLowerCase();

  return calculateSafetyScore(trend.title, text, brand);
}

function calculateSafetyScore(
  trendTitle: string,
  text: string,
  brand: string
): BrandSafetyScore {
  let score = 10;
  const matchedCategories: string[] = [];

  // Check for unsafe keywords
  for (const [category, { keywords, severity }] of Object.entries(UNSAFE_KEYWORDS)) {
    for (const keyword of keywords) {
      if (text.includes(keyword)) {
        score -= severity;
        matchedCategories.push(category.replace('_', ' '));
        break; // Only count each category once
      }
    }
  }

  // Check for brand conflict (competitor mentions)
  // For simplicity, we'll just check if the brand name appears
  // In a real system, you'd have a list of competitor brands
  const brandLower = brand.toLowerCase();
  if (brandLower && text.includes(brandLower)) {
    // Positive brand mention is actually good for relevance
    // We won't penalize here
  }

  // Clamp score to 1-10 range
  score = Math.max(1, Math.min(10, score));

  // Determine level
  let level: 'safe' | 'caution' | 'unsafe';
  if (score >= 8) {
    level = 'safe';
  } else if (score >= 5) {
    level = 'caution';
  } else {
    level = 'unsafe';
  }

  // Generate reasoning
  let reasoning: string;
  if (matchedCategories.length === 0) {
    reasoning = 'No brand safety concerns detected.';
  } else {
    const categoriesText = matchedCategories.join(', ');
    reasoning = `Flagged for: ${categoriesText}. Score reduced to ${score}/10.`;
  }

  return {
    trendTitle,
    score,
    level,
    reasoning,
  };
}
