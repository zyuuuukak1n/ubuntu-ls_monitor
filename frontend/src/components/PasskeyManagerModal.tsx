import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Edit2, Check, X, AlertCircle } from 'lucide-react';
import { api, CredentialInfo } from '../lib/api';
import { addAdditionalPasskey } from '../lib/webauthn';

interface PasskeyManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PasskeyManagerModal: React.FC<PasskeyManagerModalProps> = ({ isOpen, onClose }) => {
  const [credentials, setCredentials] = useState<CredentialInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [newKeyName, setNewKeyName] = useState('New Device Passkey');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const loadCredentials = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listCredentials();
      setCredentials(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadCredentials();
    }
  }, [isOpen]);

  const handleAddPasskey = async () => {
    setIsRegistering(true);
    setError(null);
    try {
      await addAdditionalPasskey(newKeyName.trim() || 'New Passkey');
      setNewKeyName('New Device Passkey');
      await loadCredentials();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsRegistering(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to remove this passkey?')) return;
    try {
      await api.deleteCredential(id);
      await loadCredentials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStartRename = (cred: CredentialInfo) => {
    setEditingId(cred.id);
    setEditName(cred.name);
  };

  const handleSaveRename = async (id: string) => {
    try {
      await api.renameCredential(id, editName.trim());
      setEditingId(null);
      await loadCredentials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-full max-w-xl rounded-2xl p-6 border border-slate-700 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Registered Passkeys</h3>
              <p className="text-xs text-slate-400">Manage FIDO2 / WebAuthn authenticators</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* List of keys */}
        <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1 mb-5">
          {credentials.map((cred) => (
            <div
              key={cred.id}
              className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between gap-3 text-xs"
            >
              <div className="flex-1 min-w-0">
                {editingId === cred.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="px-2 py-0.5 bg-slate-950 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-amber-400"
                    />
                    <button
                      onClick={() => handleSaveRename(cred.id)}
                      className="p-1 text-emerald-400 hover:text-emerald-300"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="p-1 text-slate-500 hover:text-slate-400"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white truncate">{cred.name}</span>
                    <button
                      onClick={() => handleStartRename(cred)}
                      className="text-slate-500 hover:text-slate-300"
                      title="Rename"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                  </div>
                )}
                <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                  Sign Count: {cred.sign_count} • Last used:{' '}
                  {cred.last_used_at ? new Date(cred.last_used_at).toLocaleDateString() : 'Never'}
                </div>
              </div>

              <button
                onClick={() => handleDelete(cred.id)}
                disabled={credentials.length <= 1}
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-20 disabled:cursor-not-allowed transition"
                title={credentials.length <= 1 ? 'Cannot delete the only registered passkey' : 'Delete passkey'}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}

          {credentials.length === 0 && !isLoading && (
            <div className="py-6 text-center text-xs text-slate-500">No credentials found.</div>
          )}
        </div>

        {/* Add new passkey section */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <label className="block text-xs font-medium text-slate-300 mb-2">Register Additional Passkey</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g. MacBook Touch ID, YubiKey 5C"
              className="flex-1 px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-amber-400"
            />
            <button
              onClick={handleAddPasskey}
              disabled={isRegistering}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 flex items-center gap-1.5 disabled:opacity-50 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{isRegistering ? 'Registering...' : 'Add Key'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
