import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

interface ArtifactDisplayProps {
  artifactUrl: string;
  artifactKey: string;
  type: 'image' | 'video';
}

export function ArtifactDisplay({ artifactUrl, artifactKey, type }: ArtifactDisplayProps) {
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadArtifact = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Try to fetch the artifact data from the API
        const response = await fetch(artifactUrl);
        
        // First, let's see what content type we're getting
        const contentType = response.headers.get('content-type');
        console.log('[ArtifactDisplay] Response content-type:', contentType);
        
        let data;
        if (contentType && contentType.includes('application/json')) {
          data = await response.json();
        } else {
          // If it's not JSON, it might be the raw file
          const blob = await response.blob();
          console.log('[ArtifactDisplay] Got blob response:', blob.type, blob.size);
          if (blob.size > 0) {
            const url = URL.createObjectURL(blob);
            setMediaUrl(url);
            return;
          }
          throw new Error('Empty response from artifact API');
        }
        
        console.log('[ArtifactDisplay] API Response:', response.status, data);
        
        if (!response.ok || data?.detail === 'Artifact not found') {
          // If artifact not found via API, show a placeholder
          console.log('[ArtifactDisplay] Artifact not found in API, showing placeholder');
          
          // Since artifacts are stored in GCS but not accessible through ADK's artifact API,
          // we'll show a message indicating the artifact was generated
          setError(`${type === 'image' ? 'Image' : 'Video'} generated: ${artifactKey}\n\nNote: Direct display of artifacts requires backend updates to include GCS URLs in the response.`);
          return;
        }
        
        // The response contains a Part object with either inline_data or file_data
        if (data?.inline_data?.data || data?.inlineData?.data) {
          const inlineData = data.inline_data || data.inlineData;
          const mimeType = inlineData.mime_type || inlineData.mimeType || (type === 'image' ? 'image/png' : 'video/mp4');
          
          try {
            // The data might already be a Uint8Array or might be base64
            let bytes;
            console.log('[ArtifactDisplay] Data type:', typeof inlineData.data, 'Data preview:', 
              typeof inlineData.data === 'string' ? inlineData.data.substring(0, 100) : inlineData.data);
            
            if (typeof inlineData.data === 'string') {
              try {
                // First check if it's valid base64 by testing a small portion
                const testString = inlineData.data.substring(0, 100);
                
                // Remove any whitespace that might be causing issues
                let cleanData = inlineData.data.replace(/\s/g, '');
                
                // Check if it's a data URL
                if (cleanData.startsWith('data:')) {
                  // Extract base64 part from data URL
                  const base64Part = cleanData.split(',')[1];
                  bytes = Uint8Array.from(atob(base64Part), c => c.charCodeAt(0));
                } else {
                  // Check if padding is needed first (before URL-safe conversion)
                  const paddingNeeded = cleanData.length % 4;
                  if (paddingNeeded) {
                    cleanData += '='.repeat(4 - paddingNeeded);
                    console.log('[ArtifactDisplay] Added padding:', 4 - paddingNeeded);
                  }
                  
                  // Convert URL-safe base64 to standard base64 (if needed)
                  cleanData = cleanData.replace(/-/g, '+').replace(/_/g, '/');
                  
                  // Try to decode as base64
                  bytes = Uint8Array.from(atob(cleanData), c => c.charCodeAt(0));
                }
              } catch (e) {
                console.error('[ArtifactDisplay] Base64 decode error:', e);
                console.error('[ArtifactDisplay] First 200 chars of data:', inlineData.data.substring(0, 200));
                console.error('[ArtifactDisplay] Data length:', inlineData.data.length);
                throw new Error(`Invalid base64 data: ${e.message}`);
              }
            } else if (inlineData.data instanceof Array) {
              // It's already an array of bytes
              bytes = new Uint8Array(inlineData.data);
            } else if (inlineData.data instanceof Uint8Array) {
              // It's already a Uint8Array
              bytes = inlineData.data;
            } else if (typeof inlineData.data === 'object' && inlineData.data !== null) {
              // It might be an object with numeric keys (like {0: 255, 1: 216, ...})
              const values = Object.values(inlineData.data);
              if (values.every(v => typeof v === 'number')) {
                bytes = new Uint8Array(values);
              } else {
                throw new Error('Unknown object format for inline data');
              }
            } else {
              throw new Error('Unknown data format for inline data');
            }
            
            const blob = new Blob([bytes], { type: mimeType });
            const url = URL.createObjectURL(blob);
            setMediaUrl(url);
          } catch (decodeError) {
            console.error('[ArtifactDisplay] Error decoding inline data:', decodeError);
            console.error('[ArtifactDisplay] Full inline data object:', inlineData);
            throw new Error(`Failed to decode ${type} data: ${decodeError.message}`);
          }
        } else if (data?.file_data?.file_uri || data?.fileData?.fileUri) {
          // Use the file URI directly (for GCS URLs)
          const fileUri = data.file_data?.file_uri || data.fileData?.fileUri;
          setMediaUrl(fileUri);
        } else if (data === null) {
          // Null response means artifact exists but has no data
          throw new Error('Artifact exists but contains no data');
        } else {
          console.error('[ArtifactDisplay] Unexpected response structure:', data);
          throw new Error('No media data found in artifact response');
        }
      } catch (err) {
        console.error('Error loading artifact:', err);
        setError(err instanceof Error ? err.message : 'Failed to load artifact');
      } finally {
        setLoading(false);
      }
    };

    loadArtifact();

    // Cleanup blob URL on unmount
    return () => {
      if (mediaUrl && mediaUrl.startsWith('blob:')) {
        URL.revokeObjectURL(mediaUrl);
      }
    };
  }, [artifactUrl, type]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-neutral-900 rounded-lg">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          {type === 'image' ? '🖼️' : '🎥'}
          <span className="text-sm font-medium text-neutral-200">
            {type === 'image' ? 'Image' : 'Video'} Generated
          </span>
        </div>
        <p className="text-xs text-neutral-400 whitespace-pre-wrap">{error}</p>
      </div>
    );
  }

  if (!mediaUrl) {
    return null;
  }

  return (
    <>
      {type === 'image' ? (
        <img 
          src={mediaUrl} 
          alt={`Generated image ${artifactKey}`}
          className="w-full h-auto rounded-lg"
          loading="lazy"
        />
      ) : (
        <video 
          src={mediaUrl} 
          controls
          className="w-full h-auto rounded-lg"
          preload="metadata"
        >
          Your browser does not support the video tag.
        </video>
      )}
    </>
  );
}