import React, { useState } from 'react';
import { Network, Copy, Check, Search, RefreshCw, Zap, Cpu } from 'lucide-react';
import { PortOverviewResponse } from '../lib/api';

interface PortInspectorProps {
  portData: PortOverviewResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const PortInspector: React.FC<PortInspectorProps> = ({
  portData,
  isLoading,
  onRefresh,
}) => {
  const [filter, setFilter] = useState('');
  const [copiedPort, setCopiedPort] = useState<number | null>(null);

  const handleCopy = (port: number) => {
    navigator.clipboard.writeText(port.toString());
    setCopiedPort(port);
    setTimeout(() => setCopiedPort(null), 2000);
  };

  const usedPorts = portData?.used_ports || [];
  const filtered = usedPorts.filter(
    (p) =>
      p.port.toString().includes(filter) ||
      (p.process_name && p.process_name.toLowerCase().includes(filter.toLowerCase())) ||
      p.address.includes(filter) ||
      p.proto.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-5 mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-white uppercase flex items-center gap-2">
              Listening Ports & Collision Prevention
            </h2>
            <p className="text-xs text-slate-400">
              Live bound socket inspection and automatic next available port suggestion
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-50 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-purple-400' : ''}`} />
          <span>Refresh Ports</span>
        </button>
      </div>

      {/* Suggested Port Banner */}
      {portData && (
        <div className="mb-5 p-4 rounded-xl bg-gradient-to-r from-purple-900/30 via-slate-900 to-slate-900 border border-purple-500/30 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-300">
              <Zap className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-purple-300">
                Recommended Next Available Port
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-2xl font-bold font-mono text-white tracking-tight">
                  {portData.suggested_port}
                </span>
                <span className="text-xs text-slate-400 font-normal">
                  (Safe for new backend / app deployments)
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleCopy(portData.suggested_port)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/20 transition"
            >
              {copiedPort === portData.suggested_port ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-300" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Port {portData.suggested_port}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Common Ranges Cards */}
      {portData?.common_ranges && portData.common_ranges.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-5">
          {portData.common_ranges.map((range, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs"
            >
              <div>
                <div className="text-slate-400 font-medium text-[11px] truncate">{range.label}</div>
                <div className="text-white font-mono font-bold mt-0.5">Next: {range.suggested}</div>
              </div>
              <button
                onClick={() => handleCopy(range.suggested)}
                className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
                title={`Copy port ${range.suggested}`}
              >
                {copiedPort === range.suggested ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Filter and Ports Table */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase text-slate-300">
          Currently Bound Sockets ({usedPorts.length} active)
        </span>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by port, process, IP..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-48 sm:w-64 pl-8 pr-3 py-1 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800/80 text-slate-400">
              <th className="pb-2.5 font-medium">PORT</th>
              <th className="pb-2.5 font-medium">PROTO</th>
              <th className="pb-2.5 font-medium">BIND ADDRESS</th>
              <th className="pb-2.5 font-medium">PROCESS</th>
              <th className="pb-2.5 font-medium">PID</th>
              <th className="pb-2.5 font-medium text-right">STATUS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
            {filtered.map((item, idx) => (
              <tr key={idx} className="hover:bg-slate-800/30 transition">
                <td className="py-2.5 font-bold text-cyan-400 flex items-center gap-1.5">
                  <span>{item.port}</span>
                </td>
                <td className="py-2.5 text-slate-400 uppercase">{item.proto}</td>
                <td className="py-2.5 text-slate-300">{item.address}</td>
                <td className="py-2.5 text-white font-semibold">
                  {item.process_name ? (
                    <span className="flex items-center gap-1">
                      <Cpu className="w-3 h-3 text-slate-500" />
                      {item.process_name}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">system/kernel</span>
                  )}
                </td>
                <td className="py-2.5 text-slate-400">{item.pid || '-'}</td>
                <td className="py-2.5 text-right">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-emerald-400 border border-slate-700">
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-slate-500">
                  No ports match current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
