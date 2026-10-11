import os
import pytest
from pathlib import Path

from app.editor import (
    find_whitelisted_file_config,
    read_whitelisted_file,
    save_whitelisted_file,
    run_validation_command
)

def test_path_traversal_blocked():
    """Ensures ../ path traversal sequences and unwhitelisted files are strictly blocked."""
    traversal_attacks = [
        "../../etc/passwd",
        "/etc/cloudflared/../shadow",
        "../config.yaml",
        "/etc/cloudflared/config.yml/../../../etc/hosts",
        "/var/log/auth.log"
    ]
    for attack_path in traversal_attacks:
        cfg = find_whitelisted_file_config(attack_path)
        assert cfg is None, f"Path traversal attack '{attack_path}' was not blocked!"

        success, msg, syntax = read_whitelisted_file(attack_path)
        assert success is False
        assert "Access denied" in msg

def test_save_and_backup_creation(tmp_path):
    """Tests that editing a whitelisted file creates a timestamped .bak backup file."""
    # Create test target file
    target_file = tmp_path / "test_config.yml"
    target_file.write_text("initial: true", encoding="utf-8")

    # Mock operation config dynamically
    from unittest.mock import patch
    mock_config = {
        "editable_files": [
            {
                "path": str(target_file),
                "label": "Test Config",
                "syntax": "yaml"
            }
        ]
    }

    with patch("app.editor.load_operation_config", return_value=mock_config):
        success, msg, backup_path, _ = save_whitelisted_file(
            path_str=str(target_file),
            new_content="initial: false\nupdated: true",
            do_backup=True
        )

        assert success is True
        assert backup_path is not None
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text(encoding="utf-8") == "initial: true"
        assert target_file.read_text(encoding="utf-8") == "initial: false\nupdated: true"

def test_validation_command_failure_aborts_save(tmp_path):
    """Tests that a failing validation command aborts file overwrite and keeps original intact."""
    target_file = tmp_path / "protected_config.yml"
    target_file.write_text("original: content", encoding="utf-8")

    from unittest.mock import patch
    mock_config = {
        "editable_files": [
            {
                "path": str(target_file),
                "label": "Protected Config",
                "syntax": "yaml",
                "validate_command": ["python", "-c", "import sys; sys.exit(1)"] # Intentionally failing validator
            }
        ]
    }

    with patch("app.editor.load_operation_config", return_value=mock_config):
        success, msg, backup_path, val_out = save_whitelisted_file(
            path_str=str(target_file),
            new_content="invalid: syntax",
            do_backup=True
        )

        assert success is False
        assert "Syntax validation failed" in msg
        # Target file content must remain unchanged
        assert target_file.read_text(encoding="utf-8") == "original: content"
