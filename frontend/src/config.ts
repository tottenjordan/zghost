// Agent configuration
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    artifactUrl: import.meta.env.VITE_ARTIFACT_URL || 'http://localhost:8001',
    timeout: 120000, // 2 minutes
  },
  session: {
    defaultUserId: 'u_999',
    defaultAppName: 'app',
  },
  ui: {
    maxMessageLength: 10000,
    scrollBehavior: 'smooth' as const,
  }
};