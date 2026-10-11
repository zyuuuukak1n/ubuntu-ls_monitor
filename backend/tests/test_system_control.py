import pytest
from unittest.mock import patch, MagicMock

from app.system_control import (
    is_service_whitelisted,
    is_container_whitelisted,
    restart_systemd_service,
    restart_docker_container,
    execute_host_reboot
)

def test_whitelist_membership():
    """Validates that only whitelisted services and containers return True."""
    # Whitelisted items from default config.yaml
    assert is_service_whitelisted("cloudflared") is True
    assert is_service_whitelisted("docker") is True

    # Dangerous or unauthorized services must return False
    assert is_service_whitelisted("cron") is False
    assert is_service_whitelisted("systemd-logind") is False
    assert is_service_whitelisted("sudo") is False
    assert is_service_whitelisted("; rm -rf /") is False

    # Container checks
    assert is_container_whitelisted("vaultwarden") is True
    assert is_container_whitelisted("malicious_container") is False

def test_unwhitelisted_restart_is_rejected():
    """Ensures restart functions immediately reject non-whitelisted items without invoking subprocess."""
    with patch("subprocess.run") as mock_run:
        success, msg = restart_systemd_service("unauthorized-service")
        assert success is False
        assert "not in the allowed operations whitelist" in msg
        mock_run.assert_not_called()

        c_success, c_msg = restart_docker_container("unauthorized-container")
        assert c_success is False
        assert "not in the allowed operations whitelist" in c_msg
        mock_run.assert_not_called()

def test_whitelisted_restart_invokes_safe_list():
    """Verifies that whitelisted restart executes via safe list arguments without shell=True."""
    with patch("shutil.which", return_value="/bin/systemctl"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            success, msg = restart_systemd_service("cloudflared")
            assert success is True
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            # Verify command is passed as a list
            assert args[0] == ["sudo", "/bin/systemctl", "restart", "cloudflared"]
            # shell=True MUST be False
            assert kwargs.get("shell") is False
