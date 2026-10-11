import React, { useState, useEffect } from 'react';
import { ShieldCheck, UserPlus, Fingerprint, AlertCircle } from 'lucide-react';
import { loginWithPasskey, registerWithInvite } from '../lib/webauthn';
import { UserProfile } from '../lib/api';

interface AuthModalProps {
  isOpen: boolean;
  onSuccess: (user: UserProfile) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onSuccess }) => {
  const [mode, setMode] = useState<'login' | 'invite'>('login');
  const [username, setUsername] = useState('');
  const [inviteToken, setInviteToken] = useState('');
  const [keyName, setKeyName] = useState('Primary Device');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check URL hash for #invite=token
  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.includes('invite=')) {
      const token = hash.split('invite=')[1]?.split('&')[0];
      if (token) {
        setInviteToken(token);
        setMode('invite');
      }
    }
  }, []);

  if (!isOpen) return null;

  const handleLogin = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await loginWithPasskey(username.trim() || undefined);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Passkey login failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteToken.trim() || !username.trim()) {
      setError('Username and invite token are required.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await registerWithInvite(inviteToken.trim(), username.trim(), keyName.trim());
      // Clean up hash from URL
      window.history.replaceState(null, '', window.location.pathname);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0a0d14]/90 backdrop-blur-md">
      <div className="glass-panel w-full max-w-md rounded-2xl p-6 sm:p-8 border border-slate-700 shadow-2xl animate-scale-in">
        <div className="text-center mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-cyan-400 mb-3">
            <Fingerprint className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Ubuntu-LS Monitor</h2>
          <p className="text-xs text-slate-400 mt-1">FIDO2 / WebAuthn Passwordless Authentication</p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {/* Tab switch */}
        <div className="grid grid-cols-2 p-1 bg-slate-900 border border-slate-800 rounded-xl mb-6 text-xs font-medium">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`py-2 rounded-lg transition ${
              mode === 'login' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Passkey Login
          </button>
          <button
            type="button"
            onClick={() => setMode('invite')}
            className={`py-2 rounded-lg transition ${
              mode === 'invite' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Invite Registration
          </button>
        </div>

        {mode === 'login' ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Username <span className="text-slate-500 font-normal">(Optional if using discoverable credentials)</span>
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. zyuuuukak1n"
                className="w-full px-3.5 py-2 text-xs bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <button
              onClick={handleLogin}
              disabled={isLoading}
              className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 disabled:opacity-50 transition"
            >
              <Fingerprint className="w-4 h-4" />
              <span>{isLoading ? 'Verifying with Authenticator...' : 'Authenticate with Passkey'}</span>
            </button>
          </div>
        ) : (
          <form onSubmit={handleRegister} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">One-Time Invite Token</label>
              <input
                type="text"
                required
                value={inviteToken}
                onChange={(e) => setInviteToken(e.target.value)}
                placeholder="Paste token generated by CLI"
                className="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">New Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. zyuuuukak1n"
                className="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Device Label</label>
              <input
                type="text"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g. Primary MacBook"
                className="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 disabled:opacity-50 transition"
            >
              <UserPlus className="w-4 h-4" />
              <span>{isLoading ? 'Creating Passkey...' : 'Register & Create Passkey'}</span>
            </button>
          </form>
        )}

        <div className="mt-6 pt-4 border-t border-slate-800 text-center">
          <p className="text-[11px] text-slate-500 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            Hardware-backed authentication • No passwords stored
          </p>
        </div>
      </div>
    </div>
  );
};
