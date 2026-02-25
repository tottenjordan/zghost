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

export function CampaignConfig({ session, onSave }: CampaignConfigProps) {
  const [config, setConfig] = useState<CampaignConfigData>({
    brand: '',
    target_product: '',
    target_audience: '',
    key_selling_points: '',
  });
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

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

  const handleFileChange = (file: File | null) => {
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      // TODO: Upload to backend
    }
  };

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
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Brand
            </label>
            <Input
              value={config.brand}
              onChange={(e) => setConfig({ ...config, brand: e.target.value })}
              placeholder="e.g., Google Pixel"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Target Product
            </label>
            <Input
              value={config.target_product}
              onChange={(e) =>
                setConfig({ ...config, target_product: e.target.value })
              }
              placeholder="e.g., Pixel 9 Pro"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Target Audience
            </label>
            <Input
              value={config.target_audience}
              onChange={(e) =>
                setConfig({ ...config, target_audience: e.target.value })
              }
              placeholder="e.g., Tech-savvy millennials"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Key Selling Points
            </label>
            <textarea
              value={config.key_selling_points}
              onChange={(e) =>
                setConfig({ ...config, key_selling_points: e.target.value })
              }
              placeholder="e.g., AI-powered camera, long battery life, sleek design"
              rows={3}
              className="flex w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Campaign Guide (PDF)
            </label>
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
                  {pdfFile
                    ? pdfFile.name
                    : 'Drag and drop a PDF file, or click to browse'}
                </p>
              </div>
            </div>
          </div>

          <Button onClick={handleSave} className="w-full">
            Save Configuration
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
