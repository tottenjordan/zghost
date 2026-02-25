import type { SearchTrend, YTTrend } from '../types/trends';

interface TrendsData {
  searchTrends: SearchTrend[];
  ytTrends: YTTrend[];
}

/**
 * Parse trends from ADK /run response events
 * The response is an array of events with content.parts containing function responses or text
 */
export function parseTrendsFromRunResponse(response: any[]): TrendsData {
  const searchTrends: SearchTrend[] = [];
  const ytTrends: YTTrend[] = [];

  if (!Array.isArray(response)) {
    return { searchTrends, ytTrends };
  }

  // Iterate through response events
  for (const event of response) {
    if (!event?.content?.parts) continue;

    for (const part of event.content.parts) {
      // Look for function responses
      if (part.functionResponse) {
        const { name, response: fnResponse } = part.functionResponse;

        // Parse Google Search trends from get_daily_gtrends
        if (name === 'get_daily_gtrends' && fnResponse) {
          const parsed = parseGoogleTrends(fnResponse);
          searchTrends.push(...parsed);
        }

        // Parse YouTube trends from get_youtube_trends
        if (name === 'get_youtube_trends' && fnResponse) {
          const parsed = parseYouTubeTrends(fnResponse);
          ytTrends.push(...parsed);
        }
      }

      // Also check for text containing markdown tables (fallback)
      if (part.text) {
        const textSearchTrends = parseGoogleTrendsFromMarkdown(part.text);
        if (textSearchTrends.length > 0) {
          searchTrends.push(...textSearchTrends);
        }
      }
    }
  }

  return { searchTrends, ytTrends };
}

/**
 * Parse Google Search trends from function response object.
 * Actual format from get_daily_gtrends: { status: "ok", markdown_table: "| index | term | rank | refresh_date |..." }
 */
function parseGoogleTrends(response: any): SearchTrend[] {
  if (response && typeof response === 'object' && response.markdown_table) {
    return parseGoogleTrendsFromMarkdown(response.markdown_table);
  }
  return [];
}

/**
 * Parse Google Search trends from markdown table in text
 * Expected format: | term | rank | refresh_date |
 */
function parseGoogleTrendsFromMarkdown(text: string): SearchTrend[] {
  const trends: SearchTrend[] = [];

  try {
    // Look for markdown table with term, rank columns
    const lines = text.split('\n');
    let inTable = false;
    let headerParsed = false;

    for (const line of lines) {
      const trimmed = line.trim();

      // Detect table header
      if (trimmed.includes('term') && trimmed.includes('rank') && trimmed.includes('|')) {
        inTable = true;
        continue;
      }

      // Skip separator line
      if (inTable && trimmed.match(/^\|[\s-:|]+\|$/)) {
        headerParsed = true;
        continue;
      }

      // Parse table rows — columns: | index | term | rank | refresh_date |
      if (inTable && headerParsed && trimmed.startsWith('|')) {
        const cells = trimmed.split('|').map(c => c.trim()).filter(c => c);
        if (cells.length >= 3) {
          const term = cells[1]; // term is 2nd column
          const rank = parseInt(cells[2], 10); // rank is 3rd column
          if (term && !isNaN(rank)) {
            trends.push({
              rank,
              title: term,
              formattedTraffic: 'N/A',
              relatedQueries: '',
            });
          }
        }
      } else if (inTable && !trimmed.startsWith('|')) {
        // End of table
        break;
      }
    }
  } catch (error) {
    console.error('Error parsing Google trends from markdown:', error);
  }

  return trends;
}

/**
 * Parse YouTube trends from function response object
 * Expected format: { row_1: { videoId, videoTitle, duration, videoURL }, row_2: ..., etc. }
 */
function parseYouTubeTrends(response: any): YTTrend[] {
  const trends: YTTrend[] = [];

  try {
    if (!response || typeof response !== 'object') {
      return trends;
    }

    // The response has keys like row_1, row_2, etc.
    const rowKeys = Object.keys(response).filter(key => key.startsWith('row_'));

    for (let i = 0; i < rowKeys.length; i++) {
      const rowKey = rowKeys[i];
      const row = response[rowKey];

      if (row && typeof row === 'object') {
        trends.push({
          rank: i + 1,
          title: row.videoTitle || row.title || 'Untitled',
          videoId: row.videoId || '',
          videoUrl: row.videoURL || row.videoUrl || '',
          channelName: row.channelName || row.channel_name || 'Unknown Channel',
          channelUrl: row.channelUrl || row.channel_url || '',
          description: row.description || '',
          viewCount: row.viewCount || row.view_count || 'N/A',
          publishedTime: row.publishedTime || row.published_time || 'N/A',
          thumbnail: row.thumbnail,
        });
      }
    }
  } catch (error) {
    console.error('Error parsing YouTube trends:', error);
  }

  return trends;
}
