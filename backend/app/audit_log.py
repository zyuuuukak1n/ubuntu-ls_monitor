import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("audit")

def log_audit_event(
    action: str,
    target: str,
    status: str,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Records a structured JSON audit event to the audit log file.
    Always executes without raising exceptions to prevent halting the main request flow.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "status": status,
        "username": username or "anonymous",
        "ip_address": ip_address or "unknown",
        "details": details or {}
    }

    try:
        log_path = settings.resolved_audit_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure secure permissions on POSIX
        if not log_path.exists() and os.name != "nt":
            # Create with mode 0600
            fd = os.open(str(log_path), os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=False)
