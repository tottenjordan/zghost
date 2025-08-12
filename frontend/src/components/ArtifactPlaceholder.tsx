import { useState, useEffect } from 'react';
import { Image, Video, Loader2, AlertCircle } from 'lucide-react';
import { getGCSArtifactUrl, parseSessionInfo } from '../lib/gcs-utils';

interface ArtifactPlaceholderProps {
  artifactKey: string;
  type: 'image' | 'video' | 'pdf';
  sessionId?: string | null;
  userId?: string | null;
}

export function ArtifactPlaceholder({ artifactKey, type, sessionId, userId }: ArtifactPlaceholderProps) {
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiPath, setApiPath] = useState<string | null>(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Use provided session info first, fall back to parsing
        let effectiveUserId = userId;
        let effectiveSessionId = sessionId;
        
        if (!effectiveUserId || !effectiveSessionId) {
          const sessionInfo = parseSessionInfo();
          if (!sessionInfo) {
            throw new Error('Unable to determine session context');
          }
          effectiveUserId = effectiveUserId || sessionInfo.userId;
          effectiveSessionId = effectiveSessionId || sessionInfo.sessionId;
        }
        
        // Build the API path for error display
        const fullApiPath = `/api/apps/trends_and_insights_agent/users/${effectiveUserId}/sessions/${effectiveSessionId}/artifacts/${artifactKey}`;
        setApiPath(fullApiPath);
        
        const url = await getGCSArtifactUrl(
          artifactKey,
          effectiveUserId,
          effectiveSessionId
        );
        
        console.log(`[ArtifactPlaceholder] Generated URL for ${artifactKey}:`, url);
        setMediaUrl(url);
      } catch (err) {
        console.error('Failed to load artifact:', err);
        setError(err instanceof Error ? err.message : 'Failed to load media');
      } finally {
        setLoading(false);
      }
    };

    fetchMedia();

    // Cleanup blob URLs when component unmounts
    return () => {
      if (mediaUrl && mediaUrl.startsWith('blob:')) {
        URL.revokeObjectURL(mediaUrl);
      }
    };
  }, [artifactKey, sessionId, userId]);

  if (loading) {
    return (
      <div className="p-6 bg-neutral-800 border border-neutral-700 rounded-lg text-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400 mx-auto mb-3" />
        <p className="text-sm text-neutral-400">Loading {type}...</p>
      </div>
    );
  }

  if (error || !mediaUrl) {
    return (
      <div className="p-6 bg-neutral-800 border border-neutral-700 rounded-lg">
        <div className="flex items-center gap-3 text-amber-500 mb-3">
          <AlertCircle className="h-5 w-5" />
          <span className="font-medium">Unable to load {type}</span>
        </div>
        <div className="space-y-2">
          <div>
            <p className="text-xs text-neutral-500 mb-1">Artifact Key:</p>
            <p className="text-sm text-neutral-400 font-mono">{artifactKey}</p>
          </div>
          {apiPath && (
            <div>
              <p className="text-xs text-neutral-500 mb-1">API Path:</p>
              <p className="text-xs text-neutral-400 font-mono break-all">{apiPath}</p>
            </div>
          )}
          {error && (
            <div>
              <p className="text-xs text-neutral-500 mb-1">Error:</p>
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}
          <p className="text-xs text-neutral-600 mt-3">
            The {type} may be stored in Google Cloud Storage but cannot be accessed. 
            Ensure proper GCS permissions and ADC configuration.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-lg overflow-hidden">
      {type === 'image' ? (
        <div 
          className="relative"
          style={{
            backgroundImage: `
              repeating-conic-gradient(#f3f4f6 0% 25%, #e5e7eb 0% 50%) 50% / 20px 20px
            `,
            backgroundColor: '#f9fafb'
          }}
        >
          <img
            src={mediaUrl}
            alt={artifactKey}
            className="w-full h-auto max-h-[600px] object-contain"
            style={{
              backgroundColor: 'white',
              opacity: 1
            }}
            onError={() => setError('Failed to load image')}
            onLoad={(e) => {
              const img = e.target as HTMLImageElement;
              console.log(`[ArtifactPlaceholder] Image loaded: ${artifactKey}, dimensions: ${img.naturalWidth}x${img.naturalHeight}`);
            }}
          />
          <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm rounded-lg px-2 py-1 flex items-center gap-1">
            <Image className="h-3 w-3 text-white" />
            <span className="text-xs text-white">AI Generated</span>
          </div>
        </div>
      ) : (
        <div className="relative">
          <video
            src={mediaUrl}
            controls
            className="w-full h-auto max-h-[600px]"
            onError={() => setError('Failed to load video')}
          >
            Your browser does not support the video tag.
          </video>
          <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm rounded-lg px-2 py-1 flex items-center gap-1">
            <Video className="h-3 w-3 text-white" />
            <span className="text-xs text-white">AI Generated</span>
          </div>
        </div>
      )}
      <div className="p-3 bg-neutral-900/50">
        <p className="text-xs text-neutral-400 font-mono">{artifactKey}</p>
      </div>
    </div>
  );
}