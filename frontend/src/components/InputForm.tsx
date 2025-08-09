import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Upload, Send, X } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

interface InputFormProps {
  onSubmit: (query: string, pdfFile?: File) => Promise<void>;
  isLoading: boolean;
  showUpload?: boolean;
  setShowUpload?: (show: boolean) => void;
  embedded?: boolean;
}

export function InputForm({ onSubmit, isLoading, showUpload = false, setShowUpload, embedded = false }: InputFormProps) {
  const [query, setQuery] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() || pdfFile) {
      await onSubmit(query, pdfFile || undefined);
      setQuery('');
      setPdfFile(null);
      if (setShowUpload) setShowUpload(false);
      // Refocus the textarea after submission
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      setQuery(`use this pdf ${file.name}`);
    }
  };

  const clearFile = () => {
    setPdfFile(null);
    setQuery('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Auto-focus the textarea when the component mounts or when loading completes
  useEffect(() => {
    if (!isLoading) {
      textareaRef.current?.focus();
    }
  }, [isLoading]);

  return (
    <form onSubmit={handleSubmit} className={`${embedded ? '' : 'space-y-4'}`}>
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={pdfFile ? `PDF ready: ${pdfFile.name}` : "Enter your marketing query or start with 'hello'..."}
          className="pr-24 min-h-[80px] bg-neutral-800 border-neutral-600 text-neutral-100 placeholder:text-neutral-500 resize-none focus:bg-neutral-750 focus:border-neutral-500 transition-colors"
          disabled={isLoading}
          autoFocus
        />
        
        {pdfFile && (
          <div className="absolute top-2 right-2 flex items-center gap-2 bg-neutral-700/50 rounded-lg px-3 py-1.5">
            <span className="text-xs text-neutral-300 truncate max-w-[150px]">
              {pdfFile.name}
            </span>
            <button
              type="button"
              onClick={clearFile}
              className="text-neutral-400 hover:text-neutral-200"
              disabled={isLoading}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        {!embedded && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              variant="outline"
              disabled={isLoading}
              className="bg-neutral-800/50 border-neutral-700 text-neutral-300 hover:bg-neutral-700/50 hover:text-neutral-100"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload PDF
            </Button>
          </>
        )}
        
        <Button 
          type="submit" 
          disabled={isLoading || (!query.trim() && !pdfFile)}
          className={`${embedded ? 'w-full' : 'flex-1'} bg-blue-600 hover:bg-blue-700 text-white`}
        >
          <Send className="h-4 w-4 mr-2" />
          {isLoading ? 'Processing...' : 'Send'}
        </Button>
      </div>
    </form>
  );
}