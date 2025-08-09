import { useState } from 'react';
import { InputForm } from './InputForm';
import { SessionSelector } from './SessionSelector';

interface WelcomeScreenProps {
  handleSubmit: (query: string, pdfFile?: File) => Promise<void>;
  isLoading: boolean;
  onCancel: () => void;
  sessionId?: string | null;
  userId?: string | null;
  appName?: string | null;
  onSessionChange?: (sessionId: string) => void;
}

export function WelcomeScreen({ handleSubmit, isLoading, onCancel, sessionId, userId, appName, onSessionChange }: WelcomeScreenProps) {
  const [showUpload, setShowUpload] = useState(false);

  const exampleQueries = [
    "Labradoodles, benefits: different colors and sizes, for millennials",
    "Target Gen Z with eco-friendly pet accessories featuring rescue dogs",
    "Create viral TikTok campaign for premium dog grooming products",
    "Market hypoallergenic puppies to urban professionals with allergies"
  ];

  const handleExampleClick = (query: string) => {
    handleSubmit(query);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="min-h-full flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-4xl z-10 py-8">
          <div className="text-center space-y-8 mb-8">
          {onSessionChange && (
            <div className="flex items-center justify-center gap-4 mb-6">
              <div className="bg-neutral-900/50 backdrop-blur-md rounded-xl border border-neutral-700 p-4">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-neutral-400">Session:</span>
                  <SessionSelector
                    currentSessionId={sessionId}
                    userId={userId}
                    appName={appName}
                    onSessionChange={onSessionChange}
                  />
                </div>
              </div>
            </div>
          )}
          <h1 className="text-5xl font-bold text-white">
            Marketing Intelligence System
          </h1>
          <p className="text-xl text-neutral-300 max-w-2xl mx-auto">
            Analyze trends, conduct research, generate creative content, and produce comprehensive marketing reports powered by Google's Agent Development Kit.
          </p>
        </div>

        <div className="space-y-6">
          <div className="bg-neutral-900/50 backdrop-blur-md p-6 rounded-2xl border border-neutral-700">
            <h3 className="text-lg font-semibold text-white mb-4">Quick Start Guide</h3>
            <div className="space-y-2 text-neutral-300">
              <p>1. Start with "hello" to begin your session</p>
              <p>2. Upload a marketing guide PDF with "use this pdf"</p>
              <p>3. Select Google or YouTube trends when prompted</p>
              <p>4. Receive comprehensive research and ad campaigns</p>
            </div>
          </div>

          <div className="bg-neutral-900/50 backdrop-blur-md p-6 rounded-2xl border border-neutral-700">
            <h3 className="text-lg font-semibold text-white mb-4">Example Queries</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {exampleQueries.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleClick(query)}
                  disabled={isLoading}
                  className="text-left p-3 rounded-lg bg-neutral-800/50 border border-neutral-700 hover:bg-neutral-700/50 hover:border-neutral-600 transition-colors text-sm text-neutral-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-neutral-900/50 backdrop-blur-md p-6 rounded-2xl border border-neutral-700">
            <InputForm 
              onSubmit={handleSubmit} 
              isLoading={isLoading}
              showUpload={showUpload}
              setShowUpload={setShowUpload}
            />
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}