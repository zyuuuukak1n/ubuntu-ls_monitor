import React from 'react';
import { ShieldCheck, Server, Key, LogOut, Power, Activity } from 'lucide-react';
import { UserProfile } from '../lib/api';

interface HeaderProps {
  user: UserProfile | null;
  uptimeSeconds?: number;
  isLive: boolean;
  isBackgroundTab: boolean;
  onOpenPasskeys: () => void;
  onOpenReboot: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  uptimeSeconds = 0,
  isLive,
  isBackgroundTab,
  onOpenPasskeys,
  onOpenReboot,
  onLogout,
}) => {
  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  return (
    <header className="sticky top-0 z-30 glass-panel border-b border-slate-800/80 px-4 lg:px-8 py-3.5 mb-6">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600/30 to-cyan-500/20 border border-blue-500/40 text-cyan-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                Ubuntu-LS Monitor
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> FIDO2 Secure
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">Home Server Operations & Sandboxed Control</p>
          </div>
        </div>

        {/* Live Indicator & Server Stats */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800">
            <span
              className={`w-2 h-2 rounded-full ${
                isBackgroundTab
                  ? 'bg-amber-400 animate-none'
                  : isLive
                  ? 'bg-emerald-400 animate-ping'
                  : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-300 font-medium">
              {isBackgroundTab ? 'Sleeping (Tab Inactive)' : isLive ? 'Live SSE Stream' : 'Disconnected'}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>Uptime: <strong className="text-white font-mono">{formatUptime(uptimeSeconds)}</strong></span>
          </div>

          {/* Action buttons */}
          {user && (
            <div className="flex items-center space-x-2">
              <button
                onClick={onOpenPasskeys}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                title="Manage Passkeys"
              >
                <Key className="w-3.5 h-3.5 text-amber-400" />
                <span className="hidden md:inline font-medium">Passkeys</span>
              </button>

              <button
                onClick={onOpenReboot}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition"
                title="Reboot Server"
              >
                <Power className="w-3.5 h-3.5 text-rose-400" />
                <span className="hidden md:inline font-medium">Reboot</span>
              </button>

              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
