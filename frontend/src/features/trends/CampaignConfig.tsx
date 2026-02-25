import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import type { Session } from '../../types/session';

interface CampaignConfigProps {
  session: Session | null;
  onSave: (config: CampaignConfigData) => void;
}

export interface CampaignConfigData {
  brand: string;
  target_product: string;
  target_audience: string;
  key_selling_points: string;
}

const PRESETS = [
  {
    label: 'Select a preset...',
    config: null,
  },
  {
    label: 'Google Pixel 9 Pro',
    config: {
      brand: 'Google Pixel',
      target_product: 'Pixel 9 Pro',
      target_audience: 'Tech-savvy millennials and Gen Z creators who value AI-powered photography',
      key_selling_points: 'AI-powered camera with Best Take, Magic Eraser, Tensor G4 chip, 7 years of updates, Gemini AI built-in',
    },
  },
  {
    label: "McDonald's McRib",
    config: {
      brand: "McDonald's",
      target_product: 'McRib Sandwich',
      target_audience: 'Fast food enthusiasts, nostalgia-driven adults 25-45',
      key_selling_points: 'Limited-time classic, seasoned boneless pork, tangy BBQ sauce, back by popular demand',
    },
  },
  {
    label: 'Nike Air Max',
    config: {
      brand: 'Nike',
      target_product: 'Air Max Dn',
      target_audience: 'Sneaker enthusiasts and streetwear culture, ages 18-35',
      key_selling_points: 'Dynamic Air technology, bold colorways, all-day comfort, street-to-gym versatility',
    },
  },
];

export function CampaignConfig({ session, onSave }: CampaignConfigProps) {
  const [config, setConfig] = useState<CampaignConfigData>({
    brand: '',
    target_product: '',
    target_audience: '',
    key_selling_points: '',
  });
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [touched, setTouched] = useState({
    brand: false,
    target_product: false,
    target_audience: false,
    key_selling_points: false,
  });

  // Load from session state
  useEffect(() => {
    if (session?.state) {
      setConfig({
        brand: session.state.brand || '',
        target_product: session.state.target_product || '',
        target_audience: session.state.target_audience || '',
        key_selling_points: session.state.key_selling_points || '',
      });
    }
  }, [session]);

  const handleSave = () => {
    onSave(config);
  };

  const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedIndex = parseInt(e.target.value);
    if (selectedIndex > 0) {
      const preset = PRESETS[selectedIndex];
      if (preset.config) {
        setConfig(preset.config);
        // Mark all fields as touched when loading a preset
        setTouched({
          brand: true,
          target_product: true,
          target_audience: true,
          key_selling_points: true,
        });
      }
    }
  };

  const handleFieldChange = (field: keyof CampaignConfigData, value: string) => {
    setConfig({ ...config, [field]: value });
  };

  const handleFieldBlur = (field: keyof CampaignConfigData) => {
    setTouched({ ...touched, [field]: true });
  };

  const handleFileChange = (file: File | null) => {
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      // Send message to backend indicating PDF upload
      // The backend expects messages in format "use this pdf [filename]"
      console.log(`PDF selected: ${file.name}. Message would be sent: "use this pdf ${file.name}"`);
    }
  };

  const handleRemovePdf = () => {
    setPdfFile(null);
  };

  const isFormValid = config.brand.trim() !== '' && config.target_product.trim() !== '';
  const showBrandError = touched.brand && config.brand.trim() === '';
  const showProductError = touched.target_product && config.target_product.trim() === '';

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileChange(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaign Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Preset dropdown */}
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Load Preset
            </label>
            <select
              onChange={handlePresetChange}
              className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              {PRESETS.map((preset, index) => (
                <option key={index} value={index}>
                  {preset.label}
                </option>
              ))}
            </select>
          </div>

          {/* Two-column grid for form fields */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Brand <span className="text-red-500">*</span>
              </label>
              <p className="mb-2 text-xs text-zinc-500">
                The company or brand name for the campaign
              </p>
              <div className="relative">
                <Input
                  value={config.brand}
                  onChange={(e) => handleFieldChange('brand', e.target.value)}
                  onBlur={() => handleFieldBlur('brand')}
                  placeholder="e.g., Google Pixel"
                  className={`${
                    showBrandError
                      ? 'border-red-500'
                      : config.brand.trim() !== ''
                      ? 'border-l-4 border-l-green-500'
                      : ''
                  }`}
                />
                {config.brand.trim() !== '' && !showBrandError && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500">
                    ✓
                  </span>
                )}
              </div>
              {showBrandError && (
                <p className="mt-1 text-xs text-red-500">Brand is required</p>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Target Product <span className="text-red-500">*</span>
              </label>
              <p className="mb-2 text-xs text-zinc-500">
                The specific product or service being promoted
              </p>
              <div className="relative">
                <Input
                  value={config.target_product}
                  onChange={(e) => handleFieldChange('target_product', e.target.value)}
                  onBlur={() => handleFieldBlur('target_product')}
                  placeholder="e.g., Pixel 9 Pro"
                  className={`${
                    showProductError
                      ? 'border-red-500'
                      : config.target_product.trim() !== ''
                      ? 'border-l-4 border-l-green-500'
                      : ''
                  }`}
                />
                {config.target_product.trim() !== '' && !showProductError && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500">
                    ✓
                  </span>
                )}
              </div>
              {showProductError && (
                <p className="mt-1 text-xs text-red-500">Target product is required</p>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Target Audience
              </label>
              <p className="mb-2 text-xs text-zinc-500">
                Who the campaign is targeting (demographics, interests)
              </p>
              <div className="relative">
                <Input
                  value={config.target_audience}
                  onChange={(e) => handleFieldChange('target_audience', e.target.value)}
                  onBlur={() => handleFieldBlur('target_audience')}
                  placeholder="e.g., Tech-savvy millennials"
                  className={`${
                    config.target_audience.trim() !== ''
                      ? 'border-l-4 border-l-green-500'
                      : ''
                  }`}
                />
                {config.target_audience.trim() !== '' && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500">
                    ✓
                  </span>
                )}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Key Selling Points
              </label>
              <p className="mb-2 text-xs text-zinc-500">
                The main benefits and features to highlight
              </p>
              <div className="relative">
                <textarea
                  value={config.key_selling_points}
                  onChange={(e) => handleFieldChange('key_selling_points', e.target.value)}
                  onBlur={() => handleFieldBlur('key_selling_points')}
                  placeholder="e.g., AI-powered camera, long battery life, sleek design"
                  rows={3}
                  className={`flex w-full rounded-md border px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                    config.key_selling_points.trim() !== ''
                      ? 'border-zinc-700 border-l-4 border-l-green-500 bg-zinc-900'
                      : 'border-zinc-700 bg-zinc-900'
                  }`}
                />
                {config.key_selling_points.trim() !== '' && (
                  <span className="absolute right-3 top-3 text-green-500">✓</span>
                )}
              </div>
            </div>
          </div>

          {/* PDF upload - full width below the grid */}
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Campaign Guide (PDF)
            </label>
            {pdfFile ? (
              <div className="rounded-lg border-2 border-green-500 bg-zinc-900/50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-green-500">✓</span>
                    <span className="text-sm text-zinc-300">{pdfFile.name}</span>
                  </div>
                  <Button
                    onClick={handleRemovePdf}
                    className="bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-1"
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ) : (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`relative rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
                  isDragging
                    ? 'border-blue-500 bg-blue-950/20'
                    : 'border-zinc-700 bg-zinc-900/50'
                }`}
              >
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                  className="absolute inset-0 cursor-pointer opacity-0"
                />
                <div className="pointer-events-none">
                  <svg
                    className="mx-auto h-12 w-12 text-zinc-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  <p className="mt-2 text-sm text-zinc-400">
                    Drag and drop a PDF file, or click to browse
                  </p>
                </div>
              </div>
            )}
          </div>

          <Button onClick={handleSave} disabled={!isFormValid} className="w-full">
            Save Configuration
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
