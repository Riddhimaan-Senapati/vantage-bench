'use client';

import { useRef, useState } from 'react';
import { Upload, CheckCircle, AlertTriangle, X, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface ProcessedResult {
  memberId: string;
  memberName: string;
  calendarPct?: number;
  status: 'ok' | 'error';
  detail?: string;
}

interface UploadResult {
  processed: ProcessedResult[];
  unmatched: string[];
}

export default function SettingsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<UploadResult | null>(null);
  const [dragging, setDragging] = useState(false);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const valid = Array.from(incoming).filter(
      (f) => f.name.endsWith('.ics') || f.name.endsWith('.zip')
    );
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...valid.filter((f) => !names.has(f.name))];
    });
    setResults(null);
  }

  function removeFile(name: string) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
    setResults(null);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }

  async function handleUpload() {
    if (!files.length) return;
    setUploading(true);
    setResults(null);
    try {
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      const res = await fetch(`${API_URL}/calendar/upload`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data: UploadResult = await res.json();
      setResults(data);
      setFiles([]);
    } catch (err) {
      setResults({
        processed: [],
        unmatched: [],
        // @ts-expect-error quick error passthrough
        error: String(err),
      });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl font-heading font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Admin controls and calendar management</p>
      </div>

      {/* Import section */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">Import Team Calendars</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload individual <code className="font-mono text-xs bg-bg-surface2 px-1 py-0.5 rounded">.ics</code> files
            named after member IDs (e.g.{' '}
            <code className="font-mono text-xs bg-bg-surface2 px-1 py-0.5 rounded">mem-001.ics</code>) or a single{' '}
            <code className="font-mono text-xs bg-bg-surface2 px-1 py-0.5 rounded">.zip</code> archive containing them.
            Each file is matched to a team member and their availability is recalculated immediately.
          </p>
        </div>

        {/* Drop zone */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            'flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-colors',
            dragging
              ? 'border-status-green bg-status-green/5'
              : 'border-border hover:border-muted-foreground/40 hover:bg-bg-surface2/50'
          )}
        >
          <Upload className="w-8 h-8 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">Drop files here or click to browse</p>
          <p className="text-xs text-muted-foreground">Accepts .ics files or a .zip archive</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".ics,.zip"
          multiple
          hidden
          onChange={(e) => addFiles(e.target.files)}
        />

        {/* Selected file chips */}
        {files.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {files.map((f) => (
              <li
                key={f.name}
                className="flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full bg-bg-surface2 border border-border text-xs text-foreground"
              >
                <FileText className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                {f.name}
                <button
                  onClick={() => removeFile(f.name)}
                  className="ml-0.5 rounded-full hover:bg-bg-surface p-0.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || files.length === 0}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            uploading || files.length === 0
              ? 'bg-bg-surface2 text-muted-foreground cursor-not-allowed'
              : 'bg-status-green text-bg-base hover:opacity-90'
          )}
        >
          <Upload className="w-4 h-4" />
          {uploading ? 'Uploading…' : 'Upload & Sync'}
        </button>

        {/* Results */}
        {results && (
          <div className="rounded-xl border border-border overflow-hidden">
            <div className="px-4 py-2.5 bg-bg-surface border-b border-border">
              <span className="text-sm font-semibold text-foreground">Upload Results</span>
            </div>
            <ul className="divide-y divide-border">
              {results.processed.map((r) => (
                <li key={r.memberId} className="flex items-center gap-3 px-4 py-3">
                  {r.status === 'ok' ? (
                    <CheckCircle className="w-4 h-4 text-status-green flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-status-amber flex-shrink-0" />
                  )}
                  <span className="flex-1 text-sm text-foreground">{r.memberName}</span>
                  {r.status === 'ok' && r.calendarPct !== undefined && (
                    <span className="font-mono text-xs text-muted-foreground">
                      cal={r.calendarPct.toFixed(1)}%
                    </span>
                  )}
                  {r.status === 'error' && (
                    <span className="text-xs text-status-red">{r.detail}</span>
                  )}
                </li>
              ))}
              {results.unmatched.map((f) => (
                <li key={f} className="flex items-center gap-3 px-4 py-3">
                  <AlertTriangle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="flex-1 text-sm text-muted-foreground">{f}</span>
                  <span className="text-xs text-muted-foreground">no matching member</span>
                </li>
              ))}
              {results.processed.length === 0 && results.unmatched.length === 0 && (
                <li className="px-4 py-3 text-sm text-muted-foreground">No files processed.</li>
              )}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
