import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CampaignStoreProvider } from '../stores/campaignStore';
import type { ReactNode } from 'react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <CampaignStoreProvider>
        {children}
      </CampaignStoreProvider>
    </QueryClientProvider>
  );
}
