import secrets
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import Request, HTTPException, Depends, status
import webauthn
from webauthn.helpers import (
    bytes_to_base64url,
    base64url_to_bytes,
    options_to_json
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    AuthenticatorTransport
)

from app.config import settings
from app.database import get_db_connection
from app.audit_log import log_audit_event

SESSION_COOKIE_NAME = "ubuntuls_session"

# ------------------------------------------------------------------------------
# Helpers: Time & Tokens
# ------------------------------------------------------------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    return utc_now().isoformat()

# ------------------------------------------------------------------------------
# Invite Token Verification
# ------------------------------------------------------------------------------
def verify_and_consume_invite(token: str, username: str) -> bool:
    """Verifies that the invite token is valid, unexpired, and unused, then marks it as used."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM invites WHERE token = ?", (token,))
            row = cursor.fetchone()
            if not row:
                return False

            if row["used"] == 1:
                return False

            expires_at = datetime.fromisoformat(row["expires_at"])
            if utc_now() > expires_at:
                return False

            # Mark as used
            cursor.execute(
                "UPDATE invites SET used = 1, used_by = ? WHERE token = ?",
                (username, token)
            )
            return True
    finally:
        conn.close()

# ------------------------------------------------------------------------------
# Challenge Management (Single-use, 60s timeout)
# ------------------------------------------------------------------------------
def store_challenge(challenge_bytes: bytes, challenge_type: str, user_id: Optional[str] = None) -> str:
    challenge_b64 = bytes_to_base64url(challenge_bytes)
    expires_at = (utc_now() + timedelta(seconds=settings.CHALLENGE_TIMEOUT_SECONDS)).isoformat()
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Clean up expired challenges
            cursor.execute("DELETE FROM challenges WHERE expires_at < ?", (utc_now_iso(),))
            cursor.execute(
                "INSERT INTO challenges (challenge, user_id, type, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (challenge_b64, user_id, challenge_type, utc_now_iso(), expires_at)
            )
    finally:
        conn.close()
    return challenge_b64

def consume_challenge(challenge_b64: str, expected_type: str) -> Optional[Dict[str, Any]]:
    """Verifies and immediately removes the challenge to prevent replay attacks."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM challenges WHERE challenge = ?", (challenge_b64,))
            row = cursor.fetchone()
            if not row:
                return None

            # Always delete to ensure single use
            cursor.execute("DELETE FROM challenges WHERE challenge = ?", (challenge_b64,))

            if row["type"] != expected_type:
                return None

            expires_at = datetime.fromisoformat(row["expires_at"])
            if utc_now() > expires_at:
                return None

            return dict(row)
    finally:
        conn.close()

# ------------------------------------------------------------------------------
# Session Management
# ------------------------------------------------------------------------------
def create_session(user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_at = (utc_now() + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)).isoformat()
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, user_id, created_at, expires_at, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, utc_now_iso(), expires_at, ip_address, user_agent)
            )
    finally:
        conn.close()
    return session_id

def destroy_session(session_id: str) -> None:
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    finally:
        conn.close()

def get_current_user_from_session(session_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.expires_at, u.id as user_id, u.username
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        if not row:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if utc_now() > expires_at:
            # Expired session
            destroy_session(session_id)
            return None

        return {
            "id": row["user_id"],
            "username": row["username"],
            "session_id": row["session_id"]
        }
    finally:
        conn.close()

async def get_current_user(request: Request) -> Dict[str, Any]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_current_user_from_session(session_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Session is invalid or expired."
        )
    return user

async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    return get_current_user_from_session(session_id)

# ------------------------------------------------------------------------------
# WebAuthn Registration Options & Verification
# ------------------------------------------------------------------------------
def get_user_verification_req() -> UserVerificationRequirement:
    val = settings.USER_VERIFICATION.lower()
    if val == "required":
        return UserVerificationRequirement.REQUIRED
    elif val == "discouraged":
        return UserVerificationRequirement.DISCOURAGED
    return UserVerificationRequirement.PREFERRED

def generate_webauthn_registration_options(user_id: str, username: str) -> Tuple[Dict[str, Any], str]:
    # Fetch existing credentials to exclude
    conn = get_db_connection()
    exclude_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM credentials WHERE user_id = ?", (user_id,))
        for row in cursor.fetchall():
            exclude_list.append(
                PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(row["id"]),
                    type=PublicKeyCredentialType.PUBLIC_KEY
                )
            )
    finally:
        conn.close()

    options = webauthn.generate_registration_options(
        rp_name=settings.RP_NAME,
        rp_id=settings.RP_ID,
        user_id=user_id.encode("utf-8"),
        user_name=username,
        user_display_name=username,
        attestation=webauthn.helpers.structs.AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=get_user_verification_req(),
            resident_key=ResidentKeyRequirement.PREFERRED
        ),
        exclude_credentials=exclude_list,
        timeout=settings.CHALLENGE_TIMEOUT_SECONDS * 1000
    )

    challenge_b64 = store_challenge(options.challenge, "registration", user_id)
    options_json = json.loads(options_to_json(options))
    return options_json, challenge_b64

def verify_webauthn_registration(
    challenge_b64: str,
    response_data: Dict[str, Any],
    credential_name: str
) -> Tuple[str, str]:
    """
    Verifies the WebAuthn registration response and stores the newly created credential.
    Returns (user_id, credential_id).
    """
    challenge_record = consume_challenge(challenge_b64, "registration")
    if not challenge_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration challenge is invalid or has expired."
        )

    user_id = challenge_record["user_id"]
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user associated with this challenge."
        )

    expected_challenge_bytes = base64url_to_bytes(challenge_b64)

    try:
        verification = webauthn.verify_registration_response(
            credential=response_data,
            expected_challenge=expected_challenge_bytes,
            expected_origin=settings.EXPECTED_ORIGIN,
            expected_rp_id=settings.RP_ID,
            require_user_verification=(settings.USER_VERIFICATION == "required")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {str(e)}"
        )

    cred_id_b64 = bytes_to_base64url(verification.credential_id)
    public_key_bytes = verification.credential_public_key
    sign_count = verification.sign_count

    transports_json = None
    if "response" in response_data and "transports" in response_data["response"]:
        transports_json = json.dumps(response_data["response"]["transports"])

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credentials (id, user_id, public_key, sign_count, transports, name, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cred_id_b64,
                user_id,
                public_key_bytes,
                sign_count,
                transports_json,
                credential_name,
                utc_now_iso(),
                utc_now_iso()
            ))
    finally:
        conn.close()

    return user_id, cred_id_b64

# ------------------------------------------------------------------------------
# WebAuthn Authentication Options & Verification
# ------------------------------------------------------------------------------
def generate_webauthn_authentication_options(username: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    conn = get_db_connection()
    allow_credentials = []
    user_id = None
    try:
        cursor = conn.cursor()
        if username:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row["id"]
                cursor.execute("SELECT id, transports FROM credentials WHERE user_id = ?", (user_id,))
                for cred_row in cursor.fetchall():
                    transports = None
                    if cred_row["transports"]:
                        try:
                            transports = [AuthenticatorTransport(t) for t in json.loads(cred_row["transports"])]
                        except Exception:
                            pass
                    allow_credentials.append(
                        PublicKeyCredentialDescriptor(
                            id=base64url_to_bytes(cred_row["id"]),
                            type=PublicKeyCredentialType.PUBLIC_KEY,
                            transports=transports
                        )
                    )
        else:
            # Allow any registered credential for discoverable credentials
            cursor.execute("SELECT id, transports FROM credentials")
            for cred_row in cursor.fetchall():
                transports = None
                if cred_row["transports"]:
                    try:
                        transports = [AuthenticatorTransport(t) for t in json.loads(cred_row["transports"])]
                    except Exception:
                        pass
                allow_credentials.append(
                    PublicKeyCredentialDescriptor(
                        id=base64url_to_bytes(cred_row["id"]),
                        type=PublicKeyCredentialType.PUBLIC_KEY,
                        transports=transports
                    )
                )
    finally:
        conn.close()

    options = webauthn.generate_authentication_options(
        rp_id=settings.RP_ID,
        user_verification=get_user_verification_req(),
        allow_credentials=allow_credentials if allow_credentials else None,
        timeout=settings.CHALLENGE_TIMEOUT_SECONDS * 1000
    )

    challenge_b64 = store_challenge(options.challenge, "authentication", user_id)
    options_json = json.loads(options_to_json(options))
    return options_json, challenge_b64

def verify_webauthn_authentication(
    challenge_b64: str,
    response_data: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Verifies authentication assertion and updates sign count.
    Detects credential cloning if sign count does not strictly increase.
    Returns (user_id, username).
    """
    challenge_record = consume_challenge(challenge_b64, "authentication")
    if not challenge_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication challenge is invalid or has expired."
        )

    raw_id = response_data.get("id") or response_data.get("rawId")
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing credential ID in authentication response."
        )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.user_id, c.public_key, c.sign_count, u.username
            FROM credentials c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        """, (raw_id,))
        cred_row = cursor.fetchone()
        if not cred_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unrecognized Passkey credential."
            )

        user_id = cred_row["user_id"]
        username = cred_row["username"]
        public_key_bytes = cred_row["public_key"]
        stored_sign_count = cred_row["sign_count"]

        expected_challenge_bytes = base64url_to_bytes(challenge_b64)

        try:
            verification = webauthn.verify_authentication_response(
                credential=response_data,
                expected_challenge=expected_challenge_bytes,
                expected_origin=settings.EXPECTED_ORIGIN,
                expected_rp_id=settings.RP_ID,
                credential_public_key=public_key_bytes,
                credential_current_sign_count=stored_sign_count,
                require_user_verification=(settings.USER_VERIFICATION == "required")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Passkey verification failed: {str(e)}"
            )

        new_sign_count = verification.new_sign_count

        # Detect clone attack: if both counts > 0 and new_sign_count <= stored_sign_count
        if stored_sign_count > 0 and new_sign_count <= stored_sign_count:
            log_audit_event(
                action="passkey_clone_detected",
                target=raw_id,
                status="failure",
                username=username,
                details={
                    "stored_count": stored_sign_count,
                    "received_count": new_sign_count
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Potential authenticator cloning attack detected. Request rejected."
            )

        with conn:
            cursor.execute("""
                UPDATE credentials
                SET sign_count = ?, last_used_at = ?
                WHERE id = ?
            """, (new_sign_count, utc_now_iso(), raw_id))

        return user_id, username
    finally:
        conn.close()
