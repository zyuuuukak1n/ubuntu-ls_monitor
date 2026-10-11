import React from 'react';
import { Cpu, HardDrive, Network, Thermometer, Layers, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { SystemMetrics } from '../lib/api';

interface MetricCardsProps {
  metrics: SystemMetrics | null;
}

export const MetricCards: React.FC<MetricCardsProps> = ({ metrics }) => {
  if (!metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 rounded-xl bg-slate-800/40 animate-pulse border border-slate-800" />
        ))}
      </div>
    );
  }

  const { cpu, memory, swap, disks, disk_io, network } = metrics;

  const getStatusColor = (percent: number) => {
    if (percent > 85) return 'bg-rose-500 text-rose-400';
    if (percent > 70) return 'bg-amber-500 text-amber-400';
    return 'bg-blue-500 text-blue-400';
  };

  const primaryTemp = cpu.temperatures && cpu.temperatures.length > 0 ? cpu.temperatures[0].current : null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. CPU Card */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-slate-400">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold uppercase tracking-wider">CPU Usage</span>
          </div>
          {primaryTemp !== null && (
            <span className="flex items-center text-xs font-mono text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              <Thermometer className="w-3 h-3 mr-0.5 text-rose-400" />
              {primaryTemp}°C
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-2xl font-bold font-mono text-white">{cpu.percent}%</span>
          <span className="text-xs text-slate-400 font-mono">
            {cpu.cores_physical}C / {cpu.cores_logical}T
          </span>
        </div>
        <div className="w-full bg-slate-800/80 rounded-full h-2 mb-3 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getStatusColor(cpu.percent).split(' ')[0]}`}
            style={{ width: `${Math.min(cpu.percent, 100)}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
          <span>Load Avg:</span>
          <span className="text-slate-300">{cpu.load_avg.join(', ')}</span>
        </div>
      </div>

      {/* 2. Memory Card */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-slate-400">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-semibold uppercase tracking-wider">RAM & Swap</span>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {memory.used_gb} / {memory.total_gb} GB
          </span>
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-2xl font-bold font-mono text-white">{memory.percent}%</span>
          <span className="text-xs text-slate-400 font-mono">Swap: {swap.percent}%</span>
        </div>
        <div className="w-full bg-slate-800/80 rounded-full h-2 mb-3 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getStatusColor(memory.percent).split(' ')[0]}`}
            style={{ width: `${Math.min(memory.percent, 100)}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
          <span>Free RAM:</span>
          <span className="text-emerald-400">{memory.free_gb} GB</span>
        </div>
      </div>

      {/* 3. Disk Card */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-slate-400">
            <HardDrive className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider">Storage & I/O</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            R:{disk_io.read_mb}MB / W:{disk_io.write_mb}MB
          </span>
        </div>
        {disks.length > 0 ? (
          <div>
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-2xl font-bold font-mono text-white">{disks[0].percent}%</span>
              <span className="text-xs text-slate-400 font-mono">
                {disks[0].used_gb} / {disks[0].total_gb} GB
              </span>
            </div>
            <div className="w-full bg-slate-800/80 rounded-full h-2 mb-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getStatusColor(disks[0].percent).split(' ')[0]}`}
                style={{ width: `${Math.min(disks[0].percent, 100)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
              <span className="truncate max-w-[120px]">{disks[0].mountpoint}</span>
              <span className="text-slate-300">Free: {disks[0].free_gb} GB</span>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500 py-4">No disks found</div>
        )}
      </div>

      {/* 4. Network Card */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-slate-400">
            <Network className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-semibold uppercase tracking-wider">Network Traffic</span>
          </div>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
            Rate
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div>
            <div className="flex items-center gap-1 text-[11px] text-slate-400">
              <ArrowDownLeft className="w-3 h-3 text-emerald-400" /> RX (Down)
            </div>
            <div className="text-lg font-bold font-mono text-white">{network.rx_kbs} <span className="text-xs font-normal text-slate-400">KB/s</span></div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-[11px] text-slate-400">
              <ArrowUpRight className="w-3 h-3 text-cyan-400" /> TX (Up)
            </div>
            <div className="text-lg font-bold font-mono text-white">{network.tx_kbs} <span className="text-xs font-normal text-slate-400">KB/s</span></div>
          </div>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-3 border-t border-slate-800/60">
          <span>Total Transfer:</span>
          <span className="text-slate-300">{(network.total_recv_mb + network.total_sent_mb).toFixed(1)} MB</span>
        </div>
      </div>
    </div>
  );
};
