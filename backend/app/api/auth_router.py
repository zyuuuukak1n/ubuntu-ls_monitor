import uuid
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, Depends, status

from app.config import settings
from app.database import get_db_connection
from app.audit_log import log_audit_event
from app.models import (
    RegisterOptionsRequest,
    RegisterVerifyRequest,
    AddCredentialOptionsRequest,
    LoginOptionsRequest,
    LoginVerifyRequest,
    UserInfoResponse,
    CredentialInfo,
    RenameCredentialRequest,
    GenericResponse
)
from app.auth import (
    verify_and_consume_invite,
    generate_webauthn_registration_options,
    verify_webauthn_registration,
    generate_webauthn_authentication_options,
    verify_webauthn_authentication,
    create_session,
    destroy_session,
    get_current_user,
    get_optional_user,
    SESSION_COOKIE_NAME,
    utc_now_iso
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ------------------------------------------------------------------------------
# Registration Flow (Invite-only)
# ------------------------------------------------------------------------------
@router.post("/register-options")
def get_register_options(req: RegisterOptionsRequest, request: Request):
    """
    Step 1 of invite-based registration.
    Validates invite token before generating WebAuthn registration challenge.
    """
    client_ip = request.client.host if request.client else "unknown"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Verify invite is valid (not consumed yet)
        cursor.execute("SELECT * FROM invites WHERE token = ? AND used = 0", (req.invite_token,))
        invite = cursor.fetchone()
        if not invite:
            log_audit_event("register_options_failed", req.username, "failure", ip_address=client_ip, details={"reason": "Invalid or used invite token"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite token.")

        # Check if username is already taken
        cursor.execute("SELECT id FROM users WHERE username = ?", (req.username,))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id = existing_user["id"]
        else:
            # Generate deterministic or random user ID
            user_id = str(uuid.uuid4())
            # Temporarily register user or keep in state until verification
            cursor.execute(
                "INSERT INTO users (id, username, created_at) VALUES (?, ?, ?)",
                (user_id, req.username, utc_now_iso())
            )
            conn.commit()

        options_json, challenge_b64 = generate_webauthn_registration_options(user_id, req.username)

        log_audit_event("register_options_generated", req.username, "success", username=req.username, ip_address=client_ip)
        return {
            "options": options_json,
            "challenge": challenge_b64,
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        log_audit_event("register_options_error", req.username, "failure", ip_address=client_ip, details={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize registration.")
    finally:
        conn.close()

@router.post("/register-verify")
def verify_register(
    req: RegisterVerifyRequest,
    invite_token: str,
    request: Request,
    response: Response
):
    """
    Step 2 of invite-based registration.
    Verifies passkey creation and consumes invite token.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Verify registration response
    user_id, cred_id = verify_webauthn_registration(
        challenge_b64=req.challenge,
        response_data=req.response,
        credential_name=req.credential_name or "Primary Passkey"
    )

    # Fetch username
    conn = get_db_connection()
    username = "unknown"
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            username = row["username"]
    finally:
        conn.close()

    # Consume invite token now
    consumed = verify_and_consume_invite(invite_token, username)
    if not consumed:
        # Rollback or log warning
        log_audit_event("register_invite_consume_failed", username, "warning", username=username, ip_address=client_ip)

    # Establish session
    user_agent = request.headers.get("user-agent", "unknown")
    session_id = create_session(user_id, ip_address=client_ip, user_agent=user_agent)

    # Set secure HTTP-only cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower(),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        path="/"
    )

    log_audit_event("user_registered", username, "success", username=username, ip_address=client_ip, details={"credential_id": cred_id})
    return {
        "success": True,
        "message": "Registration successful.",
        "user": {"id": user_id, "username": username}
    }

# ------------------------------------------------------------------------------
# Login Flow
# ------------------------------------------------------------------------------
@router.post("/login-options")
def get_login_options(req: LoginOptionsRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    options_json, challenge_b64 = generate_webauthn_authentication_options(username=req.username)
    log_audit_event("login_options_generated", req.username or "discoverable", "success", ip_address=client_ip)
    return {
        "options": options_json,
        "challenge": challenge_b64
    }

@router.post("/login-verify")
def verify_login(
    req: LoginVerifyRequest,
    request: Request,
    response: Response
):
    client_ip = request.client.host if request.client else "unknown"
    user_id, username = verify_webauthn_authentication(
        challenge_b64=req.challenge,
        response_data=req.response
    )

    user_agent = request.headers.get("user-agent", "unknown")
    session_id = create_session(user_id, ip_address=client_ip, user_agent=user_agent)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower(),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        path="/"
    )

    log_audit_event("login_success", username, "success", username=username, ip_address=client_ip)
    return {
        "success": True,
        "message": "Login successful.",
        "user": {"id": user_id, "username": username}
    }

# ------------------------------------------------------------------------------
# Session / Profile / Logout
# ------------------------------------------------------------------------------
@router.get("/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }

@router.post("/logout")
def logout(request: Request, response: Response, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    client_ip = request.client.host if request.client else "unknown"
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        destroy_session(session_id)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower()
    )

    username = user["username"] if user else "anonymous"
    log_audit_event("logout", username, "success", username=username, ip_address=client_ip)
    return {"success": True, "message": "Logged out successfully."}

# ------------------------------------------------------------------------------
# Multi-Authenticator Management (Add / List / Delete / Rename)
# ------------------------------------------------------------------------------
@router.post("/add-credential-options")
def get_add_credential_options(
    req: AddCredentialOptionsRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Generates registration options for an already authenticated user to add a new passkey."""
    options_json, challenge_b64 = generate_webauthn_registration_options(user["id"], user["username"])
    return {
        "options": options_json,
        "challenge": challenge_b64
    }

@router.post("/add-credential-verify")
def verify_add_credential(
    req: RegisterVerifyRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    user_id, cred_id = verify_webauthn_registration(
        challenge_b64=req.challenge,
        response_data=req.response,
        credential_name=req.credential_name or "Additional Passkey"
    )

    log_audit_event("credential_added", cred_id, "success", username=user["username"], ip_address=client_ip)
    return {
        "success": True,
        "message": "Passkey added successfully.",
        "credential_id": cred_id
    }

@router.get("/credentials", response_model=List[CredentialInfo])
def list_credentials(user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, sign_count, transports, created_at, last_used_at
            FROM credentials
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user["id"],))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            transports = json.loads(r["transports"]) if r["transports"] else None
            result.append(CredentialInfo(
                id=r["id"],
                name=r["name"],
                sign_count=r["sign_count"],
                transports=transports,
                created_at=r["created_at"],
                last_used_at=r["last_used_at"]
            ))
        return result
    finally:
        conn.close()

@router.delete("/credentials/{cred_id}")
def delete_credential(
    cred_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Prevent deleting the last credential to avoid lockout
            cursor.execute("SELECT COUNT(*) as cnt FROM credentials WHERE user_id = ?", (user["id"],))
            cnt = cursor.fetchone()["cnt"]
            if cnt <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the only registered Passkey. Add a new Passkey before deleting this one."
                )

            cursor.execute("DELETE FROM credentials WHERE id = ? AND user_id = ?", (cred_id, user["id"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found.")

        log_audit_event("credential_deleted", cred_id, "success", username=user["username"], ip_address=client_ip)
        return {"success": True, "message": "Credential removed successfully."}
    finally:
        conn.close()

@router.patch("/credentials/{cred_id}")
def rename_credential(
    cred_id: str,
    req: RenameCredentialRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE credentials SET name = ? WHERE id = ? AND user_id = ?",
                (req.name, cred_id, user["id"])
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found.")
        return {"success": True, "message": "Credential renamed successfully."}
    finally:
        conn.close()
