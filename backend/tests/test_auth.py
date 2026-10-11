import os
import pytest
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

# Configure test environment
os.environ["DB_PATH"] = "data/test_dashboard.db"
os.environ["AUDIT_LOG_PATH"] = "logs/test_audit.jsonl"
os.environ["CONFIG_PATH"] = "config.yaml"
os.environ["COOKIE_SECURE"] = "false"

from app.config import settings
from app.database import init_db, get_db_connection
from app.auth import (
    store_challenge,
    consume_challenge,
    verify_and_consume_invite,
    create_session,
    destroy_session,
    get_current_user_from_session,
    utc_now_iso,
    SESSION_COOKIE_NAME
)
from app.main import app

@pytest.fixture(autouse=True)
def setup_test_db():
    test_db = Path("data/test_dashboard.db")
    if test_db.exists():
        try:
            test_db.unlink()
        except OSError:
            pass
    init_db()
    yield
    if test_db.exists():
        try:
            test_db.unlink()
        except OSError:
            pass

def test_invite_token_lifecycle():
    """Tests invite creation, valid consumption, replay rejection, and expired token rejection."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    valid_expiry = (now + timedelta(minutes=15)).isoformat()
    expired_expiry = (now - timedelta(minutes=1)).isoformat()

    conn = get_db_connection()
    with conn:
        # 1. Insert valid invite
        conn.execute(
            "INSERT INTO invites (token, created_at, expires_at, used) VALUES (?, ?, ?, 0)",
            (token, now.isoformat(), valid_expiry)
        )
    conn.close()

    # First consumption succeeds
    assert verify_and_consume_invite(token, "admin_user") is True

    # Replay attack: second consumption MUST fail
    assert verify_and_consume_invite(token, "attacker") is False

    # Expired token test
    expired_token = secrets.token_urlsafe(32)
    conn = get_db_connection()
    with conn:
        conn.execute(
            "INSERT INTO invites (token, created_at, expires_at, used) VALUES (?, ?, ?, 0)",
            (expired_token, now.isoformat(), expired_expiry)
        )
    conn.close()

    assert verify_and_consume_invite(expired_token, "someone") is False

def test_challenge_single_use_and_replay_prevention():
    """Tests that WebAuthn challenge can only be consumed once and prevents replay."""
    challenge_bytes = secrets.token_bytes(32)
    challenge_b64 = store_challenge(challenge_bytes, "registration", user_id="user_123")

    # First consumption should return valid record
    record = consume_challenge(challenge_b64, "registration")
    assert record is not None
    assert record["user_id"] == "user_123"

    # Second consumption must return None (replay prevented)
    record2 = consume_challenge(challenge_b64, "registration")
    assert record2 is None

def test_unauthorized_endpoints():
    """Verifies that protected endpoints strictly return 401 Unauthorized without session."""
    client = TestClient(app)

    # 1. Metrics endpoint
    res = client.get("/api/metrics/current")
    assert res.status_code == 401

    # 2. System services endpoint
    res = client.get("/api/system/services")
    assert res.status_code == 401

    # 3. Editor files endpoint
    res = client.get("/api/editor/files")
    assert res.status_code == 401

    # 4. User profile endpoint
    res = client.get("/api/auth/me")
    assert res.status_code == 401

def test_valid_session_access():
    """Verifies that an authenticated session can access protected endpoints."""
    # Create test user
    conn = get_db_connection()
    user_id = "test_user_uuid"
    with conn:
        conn.execute(
            "INSERT INTO users (id, username, created_at) VALUES (?, ?, ?)",
            (user_id, "testadmin", utc_now_iso())
        )
    conn.close()

    session_id = create_session(user_id)

    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, session_id)

    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == "testadmin"
