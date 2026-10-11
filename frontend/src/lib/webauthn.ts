import * as webauthnJson from '@github/webauthn-json';

/**
 * Executes WebAuthn Registration via One-Time Invite Token
 */
export async function registerWithInvite(
  inviteToken: string,
  username: string,
  credentialName: string = 'Primary Passkey'
): Promise<{ success: boolean; user: { id: string; username: string } }> {
  // 1. Request registration options from backend
  const optionsRes = await fetch('/api/auth/register-options', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      invite_token: inviteToken,
      username: username.trim(),
    }),
  });

  if (!optionsRes.ok) {
    const err = await optionsRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to initiate passkey registration.');
  }

  const { options, challenge } = await optionsRes.json();

  // 2. Trigger native WebAuthn authenticator prompt
  const credentialResponse = await webauthnJson.create(options);

  // 3. Send response to backend for verification
  const verifyRes = await fetch(`/api/auth/register-verify?invite_token=${encodeURIComponent(inviteToken)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      challenge: challenge,
      response: credentialResponse,
      credential_name: credentialName,
    }),
  });

  if (!verifyRes.ok) {
    const err = await verifyRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Passkey verification failed on server.');
  }

  return verifyRes.json();
}

/**
 * Registers an additional Passkey for an already authenticated session
 */
export async function addAdditionalPasskey(
  credentialName: string = 'New Passkey'
): Promise<{ success: boolean; credential_id: string }> {
  // 1. Get options
  const optionsRes = await fetch('/api/auth/add-credential-options', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ name: credentialName }),
  });

  if (!optionsRes.ok) {
    const err = await optionsRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to initialize additional passkey.');
  }

  const { options, challenge } = await optionsRes.json();

  // 2. Invoke authenticator
  const credentialResponse = await webauthnJson.create(options);

  // 3. Verify
  const verifyRes = await fetch('/api/auth/add-credential-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      challenge: challenge,
      response: credentialResponse,
      credential_name: credentialName,
    }),
  });

  if (!verifyRes.ok) {
    const err = await verifyRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to verify new passkey.');
  }

  return verifyRes.json();
}

/**
 * Performs Passkey Login (Discoverable or with username hint)
 */
export async function loginWithPasskey(
  username?: string
): Promise<{ success: boolean; user: { id: string; username: string } }> {
  // 1. Request authentication options
  const optionsRes = await fetch('/api/auth/login-options', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username: username?.trim() || null }),
  });

  if (!optionsRes.ok) {
    const err = await optionsRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to request login options.');
  }

  const { options, challenge } = await optionsRes.json();

  // 2. Prompt authenticator (TouchID / Windows Hello / YubiKey)
  const credentialResponse = await webauthnJson.get(options);

  // 3. Verify on server
  const verifyRes = await fetch('/api/auth/login-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      challenge: challenge,
      response: credentialResponse,
    }),
  });

  if (!verifyRes.ok) {
    const err = await verifyRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Authentication assertion rejected.');
  }

  return verifyRes.json();
}
