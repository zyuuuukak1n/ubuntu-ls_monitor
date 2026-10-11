import React, { useState } from 'react';
import { Box, RefreshCw, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { DockerContainerStatus } from '../lib/api';

interface DockerControlsProps {
  containers: DockerContainerStatus[];
  onRestart: (name: string) => Promise<void>;
  onViewLogs: (containerName: string) => void;
}

export const DockerControls: React.FC<DockerControlsProps> = ({
  containers,
  onRestart,
  onViewLogs,
}) => {
  const [restarting, setRestarting] = useState<string | null>(null);

  const handleRestart = async (name: string) => {
    setRestarting(name);
    try {
      await onRestart(name);
    } finally {
      setRestarting(null);
    }
  };

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Box className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">Whitelisted Docker Containers</h2>
        </div>
        <span className="text-xs text-slate-400">Communicating via Docker Engine API</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {containers.map((c) => {
          const isRunning = c.state === 'running';
          return (
            <div
              key={c.name}
              className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex flex-col justify-between space-y-3 hover:border-slate-700 transition"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-mono text-sm font-semibold text-white truncate">{c.name}</span>
                  <span
                    className={`flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full border ${
                      isRunning
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    }`}
                  >
                    {isRunning ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                    {c.state}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-400 truncate" title={c.image}>
                  {c.image}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{c.status}</p>
              </div>

              <div className="flex items-center justify-end space-x-1.5 pt-2 border-t border-slate-800/60 text-xs">
                <button
                  onClick={() => onViewLogs(c.name)}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                  title="View docker logs"
                >
                  <FileText className="w-3 h-3 text-cyan-400" />
                  <span>Logs</span>
                </button>
                <button
                  onClick={() => handleRestart(c.name)}
                  disabled={restarting === c.name}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 disabled:opacity-50 transition"
                  title="Restart container"
                >
                  <RefreshCw className={`w-3 h-3 ${restarting === c.name ? 'animate-spin' : ''}`} />
                  <span>Restart</span>
                </button>
              </div>
            </div>
          );
        })}
        {containers.length === 0 && (
          <div className="col-span-full py-6 text-center text-xs text-slate-500">
            No active containers found in whitelist.
          </div>
        )}
      </div>
    </div>
  );
};
