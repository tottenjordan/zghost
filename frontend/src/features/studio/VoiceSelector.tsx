import { useState } from 'react';
import { Card, CardContent, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Slider } from '../../components/ui/Slider';
import { Textarea } from '../../components/ui/Textarea';
import { Badge } from '../../components/ui/Badge';
import { Mic, Play, Plus } from 'lucide-react';
import type { VoiceStyle, VoiceStyleId, VoiceSample } from './types';

const VOICE_STYLES: VoiceStyle[] = [
  { id: 'professional_male', name: 'Professional Male', languageCode: 'en-US', description: 'Professional, confident male narrator' },
  { id: 'professional_female', name: 'Professional Female', languageCode: 'en-US', description: 'Professional, warm female narrator' },
  { id: 'energetic_male', name: 'Energetic Male', languageCode: 'en-US', description: 'Upbeat, energetic male voice for youth-oriented ads' },
  { id: 'warm_female', name: 'Warm Female', languageCode: 'en-US', description: 'Warm, friendly female voice for lifestyle brands' },
  { id: 'british_male', name: 'British Male', languageCode: 'en-GB', description: 'Sophisticated British male accent' },
  { id: 'british_female', name: 'British Female', languageCode: 'en-GB', description: 'Sophisticated British female accent' },
];

interface VoiceSelectorProps {
  samples: VoiceSample[];
  selectedVoice: VoiceStyleId | null;
  onSelectVoice: (styleId: VoiceStyleId) => void;
  onGenerateSample: (config: {
    style: VoiceStyleId;
    speakingRate: number;
    pitch: number;
    script: string;
  }) => void;
}

export function VoiceSelector({
  samples,
  selectedVoice,
  onSelectVoice,
  onGenerateSample,
}: VoiceSelectorProps) {
  const [expandedStyle, setExpandedStyle] = useState<VoiceStyleId | null>(null);
  const [speakingRate, setSpeakingRate] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [script, setScript] = useState(
    'Capture life\'s moments like never before with cutting-edge AI technology.'
  );

  const handleGenerate = (styleId: VoiceStyleId) => {
    onGenerateSample({
      style: styleId,
      speakingRate,
      pitch,
      script,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mic className="h-5 w-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-zinc-50">Voice Selection</h3>
        </div>
        <Badge variant="info">{VOICE_STYLES.length} styles</Badge>
      </div>

      <p className="text-sm text-zinc-400">
        Choose a voice style for narration. Powered by Google Chirp 3 HD.
      </p>

      {/* Voice Style Grid */}
      <div className="grid gap-3 sm:grid-cols-2">
        {VOICE_STYLES.map((voice) => {
          const isSelected = selectedVoice === voice.id;
          const isExpanded = expandedStyle === voice.id;
          const voiceSamples = samples.filter((s) => s.style === voice.id);

          return (
            <Card
              key={voice.id}
              className={`cursor-pointer transition-colors ${
                isSelected
                  ? 'border-blue-500 bg-blue-950/30'
                  : 'hover:border-zinc-600'
              }`}
            >
              <CardContent className="p-4">
                <div
                  className="flex items-start justify-between"
                  onClick={() => onSelectVoice(voice.id)}
                >
                  <div className="flex-1">
                    <CardTitle className="text-sm">{voice.name}</CardTitle>
                    <p className="mt-1 text-xs text-zinc-400">
                      {voice.description}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge
                        variant={isSelected ? 'success' : 'default'}
                        className="text-xs"
                      >
                        {voice.languageCode}
                      </Badge>
                      {voiceSamples.length > 0 && (
                        <span className="text-xs text-zinc-500">
                          {voiceSamples.length} sample{voiceSamples.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  {isSelected && (
                    <div className="ml-2 h-3 w-3 rounded-full bg-blue-500" />
                  )}
                </div>

                {/* Expand/Collapse for generation controls */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedStyle(isExpanded ? null : voice.id);
                  }}
                  className="mt-3 flex w-full items-center gap-1 text-xs text-zinc-400 hover:text-zinc-300"
                >
                  <Plus className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-45' : ''}`} />
                  {isExpanded ? 'Hide controls' : 'Generate sample'}
                </button>

                {isExpanded && (
                  <div className="mt-3 space-y-3 border-t border-zinc-700 pt-3">
                    {/* Speaking Rate */}
                    <div>
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-zinc-400">
                          Speaking Rate
                        </label>
                        <span className="text-xs text-zinc-300">
                          {speakingRate.toFixed(1)}x
                        </span>
                      </div>
                      <Slider
                        min={0.5}
                        max={2.0}
                        step={0.1}
                        value={speakingRate}
                        onChange={(e) => setSpeakingRate(Number(e.target.value))}
                        className="mt-1 w-full"
                      />
                    </div>

                    {/* Pitch */}
                    <div>
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-zinc-400">Pitch</label>
                        <span className="text-xs text-zinc-300">
                          {pitch > 0 ? '+' : ''}{pitch.toFixed(1)}st
                        </span>
                      </div>
                      <Slider
                        min={-10}
                        max={10}
                        step={0.5}
                        value={pitch}
                        onChange={(e) => setPitch(Number(e.target.value))}
                        className="mt-1 w-full"
                      />
                    </div>

                    {/* Script */}
                    <div>
                      <label className="mb-1 block text-xs text-zinc-400">
                        Preview Script
                      </label>
                      <Textarea
                        value={script}
                        onChange={(e) => setScript(e.target.value)}
                        rows={2}
                        className="text-xs"
                        placeholder="Enter narration text..."
                      />
                    </div>

                    <Button
                      size="sm"
                      className="w-full"
                      onClick={() => handleGenerate(voice.id)}
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Generate Sample
                    </Button>
                  </div>
                )}

                {/* Existing samples for this voice */}
                {voiceSamples.length > 0 && (
                  <div className="mt-3 space-y-1 border-t border-zinc-700 pt-2">
                    {voiceSamples.map((sample) => (
                      <div
                        key={sample.id}
                        className="flex items-center justify-between rounded bg-zinc-800 px-2 py-1 text-xs"
                      >
                        <span className="truncate text-zinc-300">
                          {sample.label}
                        </span>
                        <Badge
                          variant={
                            sample.status === 'ready'
                              ? 'success'
                              : sample.status === 'generating'
                              ? 'info'
                              : sample.status === 'error'
                              ? 'danger'
                              : 'default'
                          }
                          className="text-xs"
                        >
                          {sample.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
