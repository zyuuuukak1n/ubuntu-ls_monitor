import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class AppSettings(BaseSettings):
    APP_ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    BASE_URL: str = "https://ubuntu-ls.zyuuuukak1n.dev"

    # WebAuthn
    RP_NAME: str = "Home Server Monitor"
    RP_ID: str = "ubuntu-ls.zyuuuukak1n.dev"
    EXPECTED_ORIGIN: str = "https://ubuntu-ls.zyuuuukak1n.dev"
    USER_VERIFICATION: str = "preferred"
    CHALLENGE_TIMEOUT_SECONDS: int = 60
    INVITE_TOKEN_EXPIRY_MINUTES: int = 15

    # Session
    SESSION_SECRET: str = Field(default="dev_secret_change_in_production_32bytes_long")
    SESSION_MAX_AGE_SECONDS: int = 86400  # 24 hours
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "strict"

    # Paths
    DB_PATH: str = "data/dashboard.db"
    CONFIG_PATH: str = "config.yaml"
    AUDIT_LOG_PATH: str = "logs/audit.jsonl"
    DOCKER_SOCKET_PATH: str = "/var/run/docker.sock"

    # CORS
    CORS_ORIGINS: str = "https://ubuntu-ls.zyuuuukak1n.dev"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def resolved_db_path(self) -> Path:
        return Path(self.DB_PATH).resolve()

    @property
    def resolved_audit_path(self) -> Path:
        return Path(self.AUDIT_LOG_PATH).resolve()

    @property
    def resolved_config_path(self) -> Path:
        return Path(self.CONFIG_PATH).resolve()

settings = AppSettings()

def load_operation_config() -> Dict[str, Any]:
    """Loads and validates the operations whitelist configuration YAML file."""
    config_file = settings.resolved_config_path
    if not config_file.exists():
        # Fallback to local default if running in development
        default_config = Path(__file__).resolve().parent.parent / "config.yaml"
        if default_config.exists():
            config_file = default_config
        else:
            return {
                "allowed_services": [],
                "allowed_containers": [],
                "editable_files": [],
                "host_reboot": {"enabled": False, "command": ["sudo", "/bin/systemctl", "reboot"]}
            }

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data
    except Exception as e:
        print(f"[ERROR] Failed to load operation config from {config_file}: {e}")
        return {
            "allowed_services": [],
            "allowed_containers": [],
            "editable_files": [],
            "host_reboot": {"enabled": False, "command": ["sudo", "/bin/systemctl", "reboot"]}
        }
