import { type Page } from '@playwright/test';

export interface CampaignConfig {
  brand: string;
  target_product: string;
  target_audience: string[];
  key_selling_points: string[];
}

/**
 * Default Pixel 9 config (matches example_state_pixel.json).
 */
export const PIXEL_PRESET: CampaignConfig = {
  brand: 'Google Pixel',
  target_product: 'Pixel 9 smartphone',
  target_audience: [
    'Demographics: millennials who follow jam bands such as Widespread Panic and Phish.',
    'Psychographics: millennials who respond positively to nostalgic messages.',
    'Lifestyle or profession: frequent travelers; spending most income on concert experiences.',
    'Hobbies, interests, humor: music lovers, attend lots of jam band concerts.',
    'Actively researching concert and music festival tickets; musical instruments.',
  ],
  key_selling_points: [
    'Best Take - Group pics, perfected. Pixel\'s Best Take combines similar photos into one fantastic picture where everyone looks their best.',
    'Night Sight + Astrophotography - Capture the cosmos with Pixel\'s signature \'Night Sight\' feature.',
    'Magic Editor - Magic Editor with Pixel lets you use generative AI to reimagine your photos.',
    'Call Screen - Goodbye, spam calls. With Call Screen, Pixel can now detect and filter out even more spam calls.',
    'Live Translate - Live Translate enables real-time translation without an app and without an internet connection.',
    'Real Tone - this feature represents the nuances of more skin tones beautifully, authentically, and accurately in photos and video.',
  ],
};

/**
 * McDonald's config for session persistence E2E test.
 */
export const MCDONALDS_PRESET: CampaignConfig = {
  brand: "McDonald's",
  target_product: 'Big Mac',
  target_audience: [
    'Demographics: Gen Z and millennials aged 18-34 in urban and suburban areas.',
    'Psychographics: value-conscious consumers who enjoy convenience and familiarity.',
    'Lifestyle: busy professionals, students, and families looking for quick meals.',
    'Interests: sports, gaming, social media trends, pop culture.',
  ],
  key_selling_points: [
    'Two all-beef patties, special sauce, lettuce, cheese, pickles, onions on a sesame seed bun — the iconic Big Mac.',
    'Available at 40,000+ locations worldwide with fast, convenient service.',
    'McDonald\'s app offers exclusive deals, rewards points, and mobile ordering.',
    'Consistent quality and taste you can count on, anywhere in the world.',
  ],
};

/**
 * Inject campaign config into localStorage so the Trends wizard is pre-filled.
 *
 * Must be called AFTER page.goto() to a same-origin page (localStorage needs a domain).
 * Call page.reload() after injection if the page has already rendered.
 */
export async function injectPreset(
  page: Page,
  config: CampaignConfig = PIXEL_PRESET,
  duration: 10 | 15 | 30 = 10,
) {
  await page.evaluate(
    ({ cfg, dur }) => {
      // Build the zustand-persisted campaign store shape
      const store = {
        state: {
          config: {
            brand: cfg.brand,
            target_product: cfg.target_product,
            target_audience: cfg.target_audience.join('; '),
            key_selling_points: cfg.key_selling_points.join('\n'),
          },
          selectedSearchTrends: [],
          selectedYtTrends: [],
          activeRubrics: [],
          sessions: [],
          activeSessionIndex: 0,
          commercialDuration: dur,
          autoStart: false,
        },
        version: 0,
      };
      localStorage.setItem('campaign-store', JSON.stringify(store));
    },
    { cfg: config, dur: duration },
  );
}
