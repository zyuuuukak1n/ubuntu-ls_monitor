import React, { useState, useEffect } from 'react';
import { FileCode, Save, ShieldAlert, CheckCircle2, RotateCcw } from 'lucide-react';
import { api, EditableFileInfo } from '../lib/api';

interface ConfigEditorProps {
  files: EditableFileInfo[];
  onRefreshFiles: () => void;
}

export const ConfigEditor: React.FC<ConfigEditorProps> = ({ files, onRefreshFiles }) => {
  const [selectedPath, setSelectedPath] = useState<string>(files[0]?.path || '');
  const [content, setContent] = useState<string>('');
  const [initialContent, setInitialContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string; detail?: string } | null>(null);

  useEffect(() => {
    if (files.length > 0 && !selectedPath) {
      setSelectedPath(files[0].path);
    }
  }, [files, selectedPath]);

  useEffect(() => {
    if (!selectedPath) return;

    let mounted = true;
    setIsLoading(true);
    setStatusMessage(null);

    api
      .getFileContent(selectedPath)
      .then((data) => {
        if (mounted) {
          setContent(data.content);
          setInitialContent(data.content);
        }
      })
      .catch((err) => {
        if (mounted) {
          setStatusMessage({ type: 'error', text: err.message });
        }
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [selectedPath]);

  const isDirty = content !== initialContent;

  const handleSave = async () => {
    if (!selectedPath) return;
    setIsSaving(true);
    setStatusMessage(null);

    try {
      const res = await api.saveFile(selectedPath, content, true);
      setInitialContent(content);
      setStatusMessage({
        type: 'success',
        text: res.message,
        detail: res.backup_path ? `Backup saved to: ${res.backup_path}` : undefined,
      });
      onRefreshFiles();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: 'Failed to save configuration file.',
        detail: err.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setContent(initialContent);
    setStatusMessage(null);
  };

  const activeFile = files.find((f) => f.path === selectedPath);

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-5 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div className="flex items-center space-x-2">
          <FileCode className="w-5 h-5 text-indigo-400" />
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
              Secure Whitelisted Config Editor
            </h2>
            <p className="text-xs text-slate-400">
              Path-traversal guarded • Automatic .bak snapshots • Dry-run syntax validation
            </p>
          </div>
        </div>

        {/* File selector */}
        <div className="flex items-center space-x-2">
          <select
            value={selectedPath}
            onChange={(e) => setSelectedPath(e.target.value)}
            className="px-3 py-1.5 text-xs font-mono bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
          >
            {files.map((f) => (
              <option key={f.path} value={f.path}>
                {f.label} ({f.path})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Editor Toolbar & Status */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-t-lg bg-slate-900 border border-b-0 border-slate-800 text-xs font-mono">
        <div className="flex items-center space-x-3 text-slate-400">
          <span className="text-white font-medium">{activeFile?.path}</span>
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-indigo-300 uppercase">
            {activeFile?.syntax}
          </span>
          {isDirty && (
            <span className="text-amber-400 font-semibold flex items-center gap-1">
              ● Unsaved Changes
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {isDirty && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Revert</span>
            </button>
          )}

          <button
            onClick={handleSave}
            disabled={!isDirty || isSaving || isLoading}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Validating & Saving...' : 'Save & Validate'}</span>
          </button>
        </div>
      </div>

      {/* Code Textarea */}
      <div className="relative">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={isLoading}
          rows={16}
          spellCheck={false}
          className="w-full p-4 font-mono text-xs text-slate-100 bg-[#070a10] border border-slate-800 rounded-b-lg focus:outline-none focus:border-indigo-500 leading-relaxed resize-y selection:bg-indigo-600"
          placeholder="# Configuration file content..."
        />
        {isLoading && (
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center text-xs text-slate-400">
            Loading file content...
          </div>
        )}
      </div>

      {/* Status Notifications */}
      {statusMessage && (
        <div
          className={`mt-3 p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
              : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-emerald-400" />
          ) : (
            <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0 text-rose-400" />
          )}
          <div className="flex-1">
            <div className="font-semibold">{statusMessage.text}</div>
            {statusMessage.detail && (
              <pre className="mt-1 font-mono text-[11px] whitespace-pre-wrap bg-slate-950/40 p-2 rounded">
                {statusMessage.detail}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
