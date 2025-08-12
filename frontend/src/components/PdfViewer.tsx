import { useState, useEffect } from 'react';
import { FileText, Loader2, AlertCircle, Maximize2, Minimize2 } from 'lucide-react';
import { getGCSArtifactUrl, parseSessionInfo } from '../lib/gcs-utils';

interface PdfViewerProps {
  artifactKey: string;
  sessionId?: string | null;
  userId?: string | null;
}

export function PdfViewer({ artifactKey, sessionId, userId }: PdfViewerProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const fetchPdf = async () => {
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
        
        const url = await getGCSArtifactUrl(
          artifactKey,
          effectiveUserId,
          effectiveSessionId
        );
        
        console.log(`[PdfViewer] Generated URL for ${artifactKey}:`, url);
        setPdfUrl(url);
      } catch (err) {
        console.error('Failed to load PDF:', err);
        setError(err instanceof Error ? err.message : 'Failed to load PDF');
      } finally {
        setLoading(false);
      }
    };

    fetchPdf();
  }, [artifactKey, sessionId, userId]);

  if (loading) {
    return (
      <div className="p-6 bg-neutral-800 border border-neutral-700 rounded-lg text-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400 mx-auto mb-3" />
        <p className="text-sm text-neutral-400">Loading PDF report...</p>
      </div>
    );
  }

  if (error || !pdfUrl) {
    return (
      <div className="p-6 bg-neutral-800 border border-neutral-700 rounded-lg">
        <div className="flex items-center gap-3 text-amber-500 mb-3">
          <AlertCircle className="h-5 w-5" />
          <span className="font-medium">Unable to load PDF</span>
        </div>
        <div className="space-y-2">
          <div>
            <p className="text-xs text-neutral-500 mb-1">Artifact Key:</p>
            <p className="text-sm text-neutral-400 font-mono">{artifactKey}</p>
          </div>
          {error && (
            <div>
              <p className="text-xs text-neutral-500 mb-1">Error:</p>
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-lg overflow-hidden">
      <div className="p-3 bg-neutral-900/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-400" />
          <p className="text-sm text-neutral-300 font-medium">PDF Report</p>
          <span className="text-xs text-neutral-500">•</span>
          <p className="text-xs text-neutral-400 font-mono">{artifactKey}</p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 hover:bg-neutral-700 rounded transition-colors"
          title={isExpanded ? "Minimize" : "Expand"}
        >
          {isExpanded ? (
            <Minimize2 className="h-4 w-4 text-neutral-400" />
          ) : (
            <Maximize2 className="h-4 w-4 text-neutral-400" />
          )}
        </button>
      </div>
      
      <div className={`relative ${isExpanded ? 'h-[80vh]' : 'h-[400px]'} transition-all duration-300`}>
        <iframe
          src={pdfUrl}
          className="w-full h-full"
          title={artifactKey}
          style={{ border: 'none' }}
        />
      </div>
      
      <div className="p-3 bg-neutral-900/50 flex items-center justify-between">
        <span className="text-xs text-neutral-500">
          {isExpanded ? 'Scroll to view full document' : 'Click expand to view larger'}
        </span>
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300"
        >
          Open in new tab →
        </a>
      </div>
    </div>
  );
}