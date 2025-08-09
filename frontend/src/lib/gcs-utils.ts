interface GCSConfig {
  bucketName?: string;
  projectId?: string;
}

/**
 * Get authenticated URL for GCS artifact
 * Uses the artifact server for direct HTTP access
 */
export async function getGCSArtifactUrl(
  artifactKey: string,
  sessionUserId: string,
  sessionId: string,
  config?: GCSConfig
): Promise<string> {
  // Import config here to get artifact server URL
  const { config: appConfig } = await import('../config');
  
  // Use the artifact server for direct HTTP access
  // This returns a shareable URL that serves the file directly
  const artifactUrl = `${appConfig.api.artifactUrl}/artifact/trends_and_insights_agent/users/${sessionUserId}/sessions/${sessionId}/artifacts/${artifactKey}`;
  
  // Return the direct URL - no need to fetch and process
  // The artifact server handles base64 decoding and serves the file with proper content type
  return artifactUrl;
}


/**
 * Parse session info from the current context
 */
export function parseSessionInfo(): { userId: string; sessionId: string } | null {
  // Try to get from URL or app state
  const pathMatch = window.location.pathname.match(/\/users\/([^\/]+)\/sessions\/([^\/]+)/);
  if (pathMatch) {
    return {
      userId: pathMatch[1],
      sessionId: pathMatch[2]
    };
  }
  
  // Default fallback
  return {
    userId: 'u_999',
    sessionId: 'current-session'
  };
}