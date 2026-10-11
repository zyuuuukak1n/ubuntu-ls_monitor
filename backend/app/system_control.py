from __future__ import annotations
import subprocess
import shutil
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

Tuple_Result = Tuple[bool, str]
from app.config import load_operation_config
from app.models import ServiceStatus, DockerContainerStatus

logger = logging.getLogger("system_control")

def get_allowed_services() -> List[Dict[str, str]]:
    cfg = load_operation_config()
    return cfg.get("allowed_services", [])

def get_allowed_containers() -> List[Dict[str, str]]:
    cfg = load_operation_config()
    return cfg.get("allowed_containers", [])

def is_service_whitelisted(service_name: str) -> bool:
    allowed = [s["name"] for s in get_allowed_services()]
    return service_name in allowed

def is_container_whitelisted(container_name: str) -> bool:
    allowed = [c["name"] for c in get_allowed_containers()]
    return container_name in allowed

# ------------------------------------------------------------------------------
# systemd Service Management
# ------------------------------------------------------------------------------
def query_systemd_services() -> List[ServiceStatus]:
    """Queries states of all whitelisted systemd services."""
    allowed = get_allowed_services()
    results = []

    has_systemctl = shutil.which("systemctl") is not None

    for item in allowed:
        sname = item["name"]
        desc = item.get("description", sname)

        if not has_systemctl:
            # Emulated / dev environment response
            results.append(ServiceStatus(
                name=sname,
                description=desc,
                active_state="active",
                sub_state="running",
                load_state="loaded",
                main_pid=1234,
                uptime="1d 4h"
            ))
            continue

        try:
            # Safe list invocation: systemctl show <service> --property=ActiveState,SubState,LoadState,MainPID
            proc = subprocess.run(
                ["systemctl", "show", sname, "--property=ActiveState,SubState,LoadState,MainPID"],
                shell=False,
                capture_output=True,
                text=True,
                timeout=5
            )
            props = {}
            for line in proc.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()

            active_state = props.get("ActiveState", "unknown")
            sub_state = props.get("SubState", "unknown")
            load_state = props.get("LoadState", "unknown")
            pid_str = props.get("MainPID", "0")
            pid = int(pid_str) if pid_str.isdigit() and int(pid_str) > 0 else None

            results.append(ServiceStatus(
                name=sname,
                description=desc,
                active_state=active_state,
                sub_state=sub_state,
                load_state=load_state,
                main_pid=pid,
                uptime=None
            ))
        except Exception as e:
            logger.warning(f"Error querying systemd service {sname}: {e}")
            results.append(ServiceStatus(
                name=sname,
                description=desc,
                active_state="error",
                sub_state="failed",
                load_state="error"
            ))

    return results

def restart_systemd_service(service_name: str) -> Tuple_Result:
    """Restarts a whitelisted systemd service with sudo."""
    if not is_service_whitelisted(service_name):
        return False, f"Service '{service_name}' is not in the allowed operations whitelist."

    if not shutil.which("systemctl"):
        return True, f"[DEV MODE] Service '{service_name}' restart simulated successfully."

    try:
        # Strictly fixed argument list with full binary path
        proc = subprocess.run(
            ["sudo", "/bin/systemctl", "restart", service_name],
            shell=False,
            capture_output=True,
            text=True,
            timeout=20
        )
        if proc.returncode == 0:
            return True, f"Service '{service_name}' restarted successfully."
        else:
            err = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
            return False, f"Failed to restart service: {err}"
    except subprocess.TimeoutExpired:
        return False, "Restart command timed out after 20 seconds."
    except Exception as e:
        return False, f"Execution failed: {str(e)}"

# ------------------------------------------------------------------------------
# Docker Container Management
# ------------------------------------------------------------------------------
def query_docker_containers() -> List[DockerContainerStatus]:
    """Queries states of whitelisted Docker containers."""
    allowed = get_allowed_containers()
    allowed_names = {c["name"] for c in allowed}
    results = []

    has_docker = shutil.which("docker") is not None

    if not has_docker:
        # Development / simulated container list
        for item in allowed:
            cname = item["name"]
            results.append(DockerContainerStatus(
                id="mock-" + cname[:8],
                name=cname,
                image=f"{cname}:latest",
                status="Up 3 hours",
                state="running",
                created="2026-10-10",
                cpu_percent=1.2,
                memory_usage="145MB / 8GB"
            ))
        return results

    try:
        # Execute safe docker ps
        proc = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=8
        )
        if proc.returncode != 0:
            logger.warning(f"docker ps returned non-zero: {proc.stderr}")
            return results

        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                names_str = data.get("Names", "")
                # Docker names might be "/container-name" or "container-name"
                name_clean = names_str.lstrip("/").split()[0] if names_str else ""
                if name_clean in allowed_names:
                    results.append(DockerContainerStatus(
                        id=data.get("ID", ""),
                        name=name_clean,
                        image=data.get("Image", ""),
                        status=data.get("Status", ""),
                        state=data.get("State", ""),
                        created=data.get("CreatedAt", ""),
                        ports=data.get("Ports", None)
                    ))
            except json.JSONDecodeError:
                continue

    except Exception as e:
        logger.error(f"Failed to inspect Docker containers: {e}")

    return results

def restart_docker_container(container_name: str) -> Tuple_Result:
    """Restarts a whitelisted Docker container."""
    if not is_container_whitelisted(container_name):
        return False, f"Container '{container_name}' is not in the allowed operations whitelist."

    if not shutil.which("docker"):
        return True, f"[DEV MODE] Container '{container_name}' restart simulated successfully."

    try:
        proc = subprocess.run(
            ["docker", "restart", container_name],
            shell=False,
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.returncode == 0:
            return True, f"Container '{container_name}' restarted successfully."
        else:
            err = proc.stderr.strip() or f"Exit code {proc.returncode}"
            return False, f"Failed to restart container: {err}"
    except subprocess.TimeoutExpired:
        return False, "Docker restart command timed out after 30 seconds."
    except Exception as e:
        return False, f"Docker execution error: {str(e)}"

# ------------------------------------------------------------------------------
# Host Reboot
# ------------------------------------------------------------------------------
def execute_host_reboot() -> Tuple_Result:
    """Executes host reboot command defined in config."""
    cfg = load_operation_config()
    reboot_cfg = cfg.get("host_reboot", {})
    if not reboot_cfg.get("enabled", False):
        return False, "Host reboot feature is disabled in operation configuration."

    cmd = reboot_cfg.get("command", ["sudo", "/bin/systemctl", "reboot"])
    if not isinstance(cmd, list) or not cmd:
        return False, "Invalid reboot command configuration."

    if not shutil.which(cmd[0]):
        return True, "[DEV MODE] Host reboot simulated successfully."

    try:
        # Trigger reboot non-blocking or short timeout
        subprocess.Popen(cmd, shell=False)
        return True, "Host reboot initiated successfully."
    except Exception as e:
        return False, f"Failed to execute reboot: {str(e)}"

