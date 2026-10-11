import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  requirePhrase?: string;
  confirmButtonText?: string;
  isDangerous?: boolean;
  onConfirm: () => Promise<void> | void;
  onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  requirePhrase,
  confirmButtonText = 'Confirm',
  isDangerous = false,
  onConfirm,
  onCancel,
}) => {
  const [inputPhrase, setInputPhrase] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const isMatch = requirePhrase ? inputPhrase.trim() === requirePhrase : true;

  const handleConfirm = async () => {
    if (!isMatch) return;
    setIsSubmitting(true);
    try {
      await onConfirm();
    } finally {
      setIsSubmitting(false);
      setInputPhrase('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-slate-700 shadow-2xl animate-scale-in">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2.5 rounded-xl border ${
                isDangerous
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}
            >
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">{title}</h3>
              <p className="text-xs text-slate-400">Strict Safety Confirmation</p>
            </div>
          </div>
          <button onClick={onCancel} className="text-slate-500 hover:text-slate-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed mb-4">{message}</p>

        {requirePhrase && (
          <div className="mb-5 p-3 rounded-lg bg-slate-900 border border-slate-800">
            <label className="block text-xs text-slate-400 mb-1.5">
              Type <strong className="text-white font-mono bg-slate-800 px-1.5 py-0.5 rounded">{requirePhrase}</strong> to proceed:
            </label>
            <input
              type="text"
              value={inputPhrase}
              onChange={(e) => setInputPhrase(e.target.value)}
              placeholder={requirePhrase}
              className="w-full px-3 py-1.5 text-xs font-mono bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-rose-500"
            />
          </div>
        )}

        <div className="flex items-center justify-end space-x-3">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!isMatch || isSubmitting}
            className={`px-4 py-2 text-xs rounded-lg font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed ${
              isDangerous ? 'bg-rose-600 hover:bg-rose-500' : 'bg-blue-600 hover:bg-blue-500'
            }`}
          >
            {isSubmitting ? 'Executing...' : confirmButtonText}
          </button>
        </div>
      </div>
    </div>
  );
};
