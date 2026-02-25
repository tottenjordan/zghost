import { VoiceBriefAssistant } from './VoiceBriefAssistant';

export function VoicePage() {
  return (
    <div className="h-full flex flex-col gap-4">
      <div>
        <h1 className="mb-2 text-3xl font-bold">Voice Brief Assistant</h1>
        <p className="text-zinc-400">
          Refine your marketing campaign brief through voice conversation
        </p>
      </div>

      <div className="flex-1 min-h-0">
        <VoiceBriefAssistant isFloating={false} />
      </div>
    </div>
  );
}
