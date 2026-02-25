import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { TrendsPage } from '../features/trends';
import { OrchestrationPage } from '../features/orchestration';
import { RatingPage } from '../features/rating';
import { StudioPage } from '../features/studio';
import { NarrativePage } from '../features/narrative';
import { VoicePage } from '../features/voice';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/trends" replace />,
      },
      {
        path: 'trends',
        element: <TrendsPage />,
      },
      {
        path: 'orchestration',
        element: <OrchestrationPage />,
      },
      {
        path: 'rating',
        element: <RatingPage />,
      },
      {
        path: 'studio',
        element: <StudioPage />,
      },
      {
        path: 'narrative',
        element: <NarrativePage />,
      },
      {
        path: 'voice',
        element: <VoicePage />,
      },
    ],
  },
]);
