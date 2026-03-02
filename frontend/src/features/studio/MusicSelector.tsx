import { useState } from 'react';
import { Card, CardContent, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Textarea } from '../../components/ui/Textarea';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { GripVertical, Music, Play, Plus, Trash2 } from 'lucide-react';
import type { MusicSample } from './types';

// Preset genres and moods matching the backend music_tools.py
const GENRE_PRESETS = [
  'upbeat pop',
  'corporate ambient',
  'indie folk',
  'electronic',
  'orchestral',
  'lo-fi hip hop',
  'cinematic',
  'acoustic',
];

const MOOD_PRESETS = [
  'inspirational',
  'energetic',
  'calm',
  'playful',
  'sophisticated',
  'dramatic',
  'warm',
  'futuristic',
];

const INSTRUMENT_PRESETS = [
  'acoustic guitar and piano',
  'synth pads',
  'full orchestra',
  'minimal percussion',
  'electric guitar and drums',
  'strings and woodwinds',
  'electronic beats and bass',
  'piano solo',
];

// Pre-configured soundtrack templates
const SOUNDTRACK_TEMPLATES = [
  {
    name: 'Tech Product Launch',
    genre: 'electronic',
    mood: 'futuristic',
    instruments: 'synth pads',
    prompt: 'Modern, sleek electronic track building to an energetic crescendo. Perfect for a tech product reveal with a sense of innovation and excitement.',
  },
  {
    name: 'Lifestyle Brand',
    genre: 'indie folk',
    mood: 'warm',
    instruments: 'acoustic guitar and piano',
    prompt: 'Warm, organic feel with gentle acoustic instruments. Evokes authenticity and connection, ideal for lifestyle and wellness brands.',
  },
  {
    name: 'Corporate Presentation',
    genre: 'corporate ambient',
    mood: 'inspirational',
    instruments: 'strings and woodwinds',
    prompt: 'Professional, uplifting ambient track with subtle orchestral elements. Builds confidence and trust without being distracting.',
  },
  {
    name: 'Youth & Energy',
    genre: 'upbeat pop',
    mood: 'energetic',
    instruments: 'electronic beats and bass',
    prompt: 'High-energy pop track with driving beat and catchy hooks. Perfect for youth-oriented campaigns with bold, dynamic visuals.',
  },
  {
    name: 'Cinematic Drama',
    genre: 'cinematic',
    mood: 'dramatic',
    instruments: 'full orchestra',
    prompt: 'Epic cinematic score with sweeping orchestral arrangement. Builds tension and releases into a powerful, memorable climax.',
  },
];

interface MusicSelectorProps {
  samples: MusicSample[];
  selectedMusicId: string | null;
  onSelectMusic: (sampleId: string) => void;
  onGenerateSample: (config: {
    prompt: string;
    durationSeconds: number;
    genre: string;
    mood: string;
    instruments: string;
  }) => void;
  onRemoveSample: (sampleId: string) => void;
}

export function MusicSelector({
  samples,
  selectedMusicId,
  onSelectMusic,
  onGenerateSample,
  onRemoveSample,
}: MusicSelectorProps) {
  const [showCustom, setShowCustom] = useState(false);
  const [genre, setGenre] = useState(GENRE_PRESETS[0]);
  const [mood, setMood] = useState(MOOD_PRESETS[0]);
  const [instruments, setInstruments] = useState(INSTRUMENT_PRESETS[0]);
  const [duration, setDuration] = useState(30);
  const [prompt, setPrompt] = useState('');

  const handleGenerateFromTemplate = (template: typeof SOUNDTRACK_TEMPLATES[0]) => {
    onGenerateSample({
      prompt: template.prompt,
      durationSeconds: 30,
      genre: template.genre,
      mood: template.mood,
      instruments: template.instruments,
    });
  };

  const handleGenerateCustom = () => {
    onGenerateSample({
      prompt: prompt || `A ${mood} ${genre} track featuring ${instruments}`,
      durationSeconds: duration,
      genre,
      mood,
      instruments,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Music className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-zinc-50">Music Selection</h3>
        </div>
        <Badge variant="info">Lyria AI</Badge>
      </div>

      <p className="text-sm text-zinc-400">
        Generate background music for your commercial. Powered by Google Lyria.
      </p>

      {/* Generated Samples */}
      {samples.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-zinc-300">Generated Tracks</h4>
          {samples.map((sample) => {
            const isSelected = selectedMusicId === sample.id;
            return (
              <Card
                key={sample.id}
                draggable={sample.status === 'ready'}
                onDragStart={(e) => {
                  if (sample.status !== 'ready') {
                    e.preventDefault();
                    return;
                  }
                  e.dataTransfer.setData('application/x-music-sample', sample.id);
                  e.dataTransfer.effectAllowed = 'copy';
                }}
                className={`transition-colors ${
                  isSelected
                    ? 'border-purple-500 bg-purple-950/30'
                    : 'hover:border-zinc-600'
                } ${sample.status === 'ready' ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer'}`}
                onClick={() => onSelectMusic(sample.id)}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-3">
                    {sample.status === 'ready' && (
                      <GripVertical className="h-4 w-4 shrink-0 text-zinc-600" />
                    )}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-800">
                      {sample.status === 'generating' ? (
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-purple-400 border-t-transparent" />
                      ) : (
                        <Music className="h-4 w-4 text-purple-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-zinc-100">
                          {sample.name}
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
                      <p className="truncate text-xs text-zinc-500">
                        {sample.genre} · {sample.mood} · {sample.durationSeconds}s
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      {isSelected && (
                        <div className="h-3 w-3 rounded-full bg-purple-500" />
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveSample(sample.id);
                        }}
                        className="rounded p-1 text-zinc-500 hover:bg-zinc-700 hover:text-zinc-300"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                  {sample.status === 'ready' && sample.url && (
                    <audio
                      src={sample.url}
                      controls
                      className="mt-2 w-full h-8"
                      preload="none"
                    />
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Soundtrack Templates */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-zinc-300">Quick Templates</h4>
        <div className="grid gap-2 sm:grid-cols-2">
          {SOUNDTRACK_TEMPLATES.map((template) => (
            <button
              key={template.name}
              onClick={() => handleGenerateFromTemplate(template)}
              className="rounded-lg border border-zinc-700 bg-zinc-800 p-3 text-left transition-colors hover:border-zinc-600 hover:bg-zinc-750"
            >
              <div className="mb-1 text-sm font-medium text-zinc-100">
                {template.name}
              </div>
              <div className="flex flex-wrap gap-1">
                <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-300">
                  {template.genre}
                </span>
                <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-300">
                  {template.mood}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Generation */}
      <div className="space-y-3">
        <button
          onClick={() => setShowCustom(!showCustom)}
          className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-300"
        >
          <Plus className={`h-4 w-4 transition-transform ${showCustom ? 'rotate-45' : ''}`} />
          {showCustom ? 'Hide custom options' : 'Custom soundtrack'}
        </button>

        {showCustom && (
          <Card>
            <CardContent className="space-y-3 p-4">
              <CardTitle className="text-sm">Custom Soundtrack</CardTitle>

              {/* Genre */}
              <div>
                <label className="mb-1 block text-xs text-zinc-400">Genre</label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {GENRE_PRESETS.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>

              {/* Mood */}
              <div>
                <label className="mb-1 block text-xs text-zinc-400">Mood</label>
                <select
                  value={mood}
                  onChange={(e) => setMood(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {MOOD_PRESETS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* Instruments */}
              <div>
                <label className="mb-1 block text-xs text-zinc-400">Instruments</label>
                <select
                  value={instruments}
                  onChange={(e) => setInstruments(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {INSTRUMENT_PRESETS.map((i) => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div>
                <label className="mb-1 block text-xs text-zinc-400">
                  Duration: {duration}s
                </label>
                <Input
                  type="number"
                  min={5}
                  max={60}
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                />
              </div>

              {/* Prompt */}
              <div>
                <label className="mb-1 block text-xs text-zinc-400">
                  Creative Direction
                </label>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the soundtrack you want..."
                  rows={3}
                  className="text-sm"
                />
              </div>

              <Button className="w-full" onClick={handleGenerateCustom}>
                <Play className="mr-1 h-4 w-4" />
                Generate Soundtrack
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
