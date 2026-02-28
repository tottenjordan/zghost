import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCampaignStore } from '../../stores/campaignStore';
import type { VoiceAction } from './types';

export function useVoiceActions() {
  const navigate = useNavigate();
  const store = useCampaignStore();

  const executeAction = useCallback((action: VoiceAction) => {
    console.log('Voice action received:', action);

    switch (action.action) {
      case 'set_campaign_config': {
        const p = action.params || {};
        store.setCampaignConfig({
          brand: p.brand || store.config.brand,
          target_product: p.product || store.config.target_product,
          target_audience: p.audience || store.config.target_audience,
          key_selling_points: p.selling_points || store.config.key_selling_points,
        });
        break;
      }

      case 'navigate_to_page': {
        const page = action.params?.page;
        if (page) {
          navigate(`/${page}`);
        }
        break;
      }

      case 'start_pipeline': {
        store.setAutoStart(true);
        navigate('/orchestration');
        break;
      }

      case 'set_commercial_duration': {
        const seconds = action.params?.seconds;
        if (seconds === 10 || seconds === 15 || seconds === 30) {
          store.setCommercialDuration(seconds);
        }
        break;
      }

      case 'select_google_trend':
      case 'select_youtube_trend':
      case 'send_narrative_direction':
      case 'send_studio_direction':
      case 'score_criterion':
        // These actions are dispatched as custom events so page-specific
        // components can handle them without tight coupling
        window.dispatchEvent(new CustomEvent('voice-action', { detail: action }));
        break;

      default:
        console.warn('Unknown voice action:', action.action);
    }
  }, [navigate, store]);

  return { executeAction };
}
