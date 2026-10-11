#!/usr/bin/env python3
"""
Ubuntu-LS Monitor CLI Management Utility.
Used on the server for bootstrapping passkey invites, database management, and administration.
"""
import sys
import os
import argparse
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import get_db_connection, init_db
from app.audit_log import log_audit_event

def cmd_init_db(args):
    """Initializes the database tables."""
    print("[*] Initializing SQLite database schema...")
    init_db()
    print(f"[+] Database successfully initialized at: {settings.resolved_db_path}")

def cmd_create_invite(args):
    """Generates a single-use 15-minute invite token and bootstrap URL."""
    # Ensure tables exist
    init_db()

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expiry_minutes = args.expiry if args.expiry else settings.INVITE_TOKEN_EXPIRY_MINUTES
    expires_at = (now + timedelta(minutes=expiry_minutes)).isoformat()

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO invites (token, created_at, expires_at, used) VALUES (?, ?, ?, 0)",
                (token, now.isoformat(), expires_at)
            )
        log_audit_event("invite_created", token, "success", username="cli_admin", details={"expires_at": expires_at})

        base_url = settings.BASE_URL.rstrip("/")
        invite_url = f"{base_url}/#invite={token}"

        print("=" * 72)
        print("          UBUNTU-LS MONITOR - ONE-TIME REGISTRATION INVITE")
        print("=" * 72)
        print(f"Token:       {token}")
        print(f"Valid For:   {expiry_minutes} minutes (Expires at: {expires_at})")
        print(f"Invite URL:  {invite_url}")
        print("=" * 72)
        print("Note: Access this URL via your WebAuthn-compatible browser (Safari, Chrome,")
        print("Edge, Firefox) to register your primary Passkey (Touch ID, Windows Hello,")
        print("or FIDO2 Security Key). This token will be permanently consumed upon registration.")
        print("=" * 72)
    finally:
        conn.close()

def cmd_list_users(args):
    """Lists registered users and their registered passkeys."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, created_at FROM users ORDER BY created_at ASC")
        users = cursor.fetchall()
        if not users:
            print("[-] No registered users found.")
            return

        print(f"{'User ID':<38} {'Username':<20} {'Created At':<25}")
        print("-" * 85)
        for u in users:
            print(f"{u['id']:<38} {u['username']:<20} {u['created_at']:<25}")
            cursor.execute("SELECT id, name, sign_count, created_at, last_used_at FROM credentials WHERE user_id = ?", (u['id'],))
            creds = cursor.fetchall()
            for c in creds:
                last_used = c['last_used_at'] or 'Never'
                print(f"   └─ Passkey: '{c['name']}' (Count: {c['sign_count']}, Last used: {last_used})")
        print("-" * 85)
    finally:
        conn.close()

def cmd_revoke_user(args):
    """Revokes and deletes a user along with all associated credentials and sessions."""
    init_db()
    username = args.username
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                print(f"[-] User '{username}' does not exist.")
                return

            user_id = row["id"]
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            print(f"[+] User '{username}' and all associated credentials/sessions were revoked.")
            log_audit_event("user_revoked", username, "success", username="cli_admin")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Ubuntu-LS Monitor Admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init-db
    p_init = subparsers.add_parser("init-db", help="Initialize the database schema")
    p_init.set_defaults(func=cmd_init_db)

    # create-invite
    p_invite = subparsers.add_parser("create-invite", help="Generate a one-time bootstrap invite token")
    p_invite.add_argument("--expiry", type=int, default=15, help="Expiry time in minutes (default: 15)")
    p_invite.set_defaults(func=cmd_create_invite)

    # list-users
    p_list = subparsers.add_parser("list-users", help="List registered users and passkeys")
    p_list.set_defaults(func=cmd_list_users)

    # revoke-user
    p_revoke = subparsers.add_parser("revoke-user", help="Revoke and delete a user")
    p_revoke.add_argument("username", type=str, help="Username to revoke")
    p_revoke.set_defaults(func=cmd_revoke_user)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
