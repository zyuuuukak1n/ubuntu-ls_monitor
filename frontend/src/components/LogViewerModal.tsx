import React, { useEffect, useRef, useState } from 'react';
import { X, Pause, Play, Download, Search, Terminal } from 'lucide-react';

interface LogViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetType: 'systemd' | 'docker';
  targetName: string;
}

export const LogViewerModal: React.FC<LogViewerModalProps> = ({
  isOpen,
  onClose,
  targetType,
  targetName,
}) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!isOpen || !targetName) return;

    setLogs([]);
    const streamUrl =
      targetType === 'systemd'
        ? `/api/logs/systemd/${encodeURIComponent(targetName)}/stream`
        : `/api/logs/docker/${encodeURIComponent(targetName)}/stream`;

    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.line !== undefined) {
          if (!isPaused) {
            setLogs((prev) => [...prev.slice(-499), data.line]);
          }
        }
      } catch {
        // raw string fallback
        if (!isPaused) {
          setLogs((prev) => [...prev.slice(-499), event.data]);
        }
      }
    };

    es.onerror = () => {
      // EventSource reconnects automatically
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [isOpen, targetType, targetName, isPaused]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  if (!isOpen) return null;

  const filteredLogs = logs.filter((line) => line.toLowerCase().includes(filter.toLowerCase()));

  const handleDownload = () => {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${targetName}_logs_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-full max-w-5xl h-[85vh] rounded-2xl flex flex-col border border-slate-700 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-2.5">
            <Terminal className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                Live Log Stream: <span className="font-mono text-cyan-400">{targetName}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">
                  {targetType}
                </span>
              </h3>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search logs..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="pl-7 pr-3 py-1 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-36 sm:w-48"
              />
            </div>

            {/* Pause / Resume */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition ${
                isPaused
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
              }`}
              title={isPaused ? 'Resume Streaming' : 'Pause Streaming'}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            </button>

            {/* Download */}
            <button
              onClick={handleDownload}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              title="Download Logs"
            >
              <Download className="w-3.5 h-3.5" />
            </button>

            {/* Close */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-400 border border-slate-700 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Console / Terminal Body */}
        <div
          ref={containerRef}
          className="flex-1 p-4 bg-[#070a10] overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed space-y-1 select-text"
        >
          {filteredLogs.map((line, idx) => (
            <div key={idx} className="hover:bg-slate-900/60 px-1 rounded flex gap-2">
              <span className="text-slate-600 select-none text-[10px] w-8 text-right shrink-0">{idx + 1}</span>
              <span className="break-all whitespace-pre-wrap">{line}</span>
            </div>
          ))}
          {filteredLogs.length === 0 && (
            <div className="h-full flex items-center justify-center text-slate-600 text-xs">
              Waiting for log entries from {targetName}...
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-2 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs text-slate-400">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
            />
            <span>Auto-scroll to latest</span>
          </label>
          <span>Buffered: {logs.length} lines</span>
        </div>
      </div>
    </div>
  );
};
