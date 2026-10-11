import React, { useState } from 'react';
import { Cog, RefreshCw, FileText, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { ServiceStatus } from '../lib/api';

interface SystemdControlsProps {
  services: ServiceStatus[];
  onRestart: (name: string) => Promise<void>;
  onViewLogs: (serviceName: string) => void;
}

export const SystemdControls: React.FC<SystemdControlsProps> = ({
  services,
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

  const getBadge = (state: string) => {
    switch (state.toLowerCase()) {
      case 'active':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> active
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3" /> failed
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            <AlertTriangle className="w-3 h-3" /> {state}
          </span>
        );
    }
  };

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Cog className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">systemd Whitelisted Services</h2>
        </div>
        <span className="text-xs text-slate-400">Restarts executed via sudo sandboxing</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex flex-col justify-between space-y-3 hover:border-slate-700 transition"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-mono text-sm font-semibold text-white truncate">{svc.name}</span>
                {getBadge(svc.active_state)}
              </div>
              <p className="text-xs text-slate-400 line-clamp-2">{svc.description}</p>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
              <span className="font-mono text-[11px] text-slate-500">
                PID: {svc.main_pid || 'none'}
              </span>
              <div className="flex items-center space-x-1.5">
                <button
                  onClick={() => onViewLogs(svc.name)}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                  title="View journalctl live log"
                >
                  <FileText className="w-3 h-3 text-cyan-400" />
                  <span>Logs</span>
                </button>
                <button
                  onClick={() => handleRestart(svc.name)}
                  disabled={restarting === svc.name}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 disabled:opacity-50 transition"
                  title="Restart service"
                >
                  <RefreshCw className={`w-3 h-3 ${restarting === svc.name ? 'animate-spin' : ''}`} />
                  <span>Restart</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
