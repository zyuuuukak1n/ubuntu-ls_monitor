import React, { useState } from 'react';
import { ListFilter, Search } from 'lucide-react';
import { SystemMetrics } from '../lib/api';

interface ProcessListProps {
  processes?: SystemMetrics['top_processes'];
}

export const ProcessList: React.FC<ProcessListProps> = ({ processes = [] }) => {
  const [filter, setFilter] = useState('');

  const filtered = processes.filter(
    (p) =>
      p.name.toLowerCase().includes(filter.toLowerCase()) ||
      p.username.toLowerCase().includes(filter.toLowerCase()) ||
      p.pid.toString().includes(filter)
  );

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-5 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center space-x-2">
          <ListFilter className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">Top Resource Consumers</h2>
          <span className="text-xs font-mono text-slate-400">({processes.length} procs)</span>
        </div>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter processes..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full sm:w-56 pl-8 pr-3 py-1 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800/80 text-slate-400">
              <th className="pb-2.5 font-medium">PID</th>
              <th className="pb-2.5 font-medium">NAME</th>
              <th className="pb-2.5 font-medium">USER</th>
              <th className="pb-2.5 font-medium text-right">CPU %</th>
              <th className="pb-2.5 font-medium text-right">MEM %</th>
              <th className="pb-2.5 font-medium text-center">STATUS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
            {filtered.map((proc) => (
              <tr key={proc.pid} className="hover:bg-slate-800/30 transition">
                <td className="py-2.5 text-slate-400">{proc.pid}</td>
                <td className="py-2.5 text-white font-medium">{proc.name}</td>
                <td className="py-2.5 text-slate-400">{proc.username}</td>
                <td className="py-2.5 text-right font-medium text-cyan-400">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden hidden sm:block">
                      <div
                        className="bg-cyan-500 h-full"
                        style={{ width: `${Math.min(proc.cpu_percent, 100)}%` }}
                      />
                    </div>
                    <span>{proc.cpu_percent}%</span>
                  </div>
                </td>
                <td className="py-2.5 text-right font-medium text-indigo-400">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden hidden sm:block">
                      <div
                        className="bg-indigo-500 h-full"
                        style={{ width: `${Math.min(proc.memory_percent, 100)}%` }}
                      />
                    </div>
                    <span>{proc.memory_percent}%</span>
                  </div>
                </td>
                <td className="py-2.5 text-center">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                    {proc.status}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-slate-500">
                  No processes match criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
