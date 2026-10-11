from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status

from app.auth import get_current_user
from app.audit_log import log_audit_event
from app.models import (
    ServiceStatus,
    DockerContainerStatus,
    ServiceRestartRequest,
    DockerRestartRequest,
    HostRebootRequest,
    GenericResponse
)
from app.system_control import (
    query_systemd_services,
    restart_systemd_service,
    query_docker_containers,
    restart_docker_container,
    execute_host_reboot,
    is_service_whitelisted,
    is_container_whitelisted
)

router = APIRouter(prefix="/api/system", tags=["system"])

# ------------------------------------------------------------------------------
# systemd Services
# ------------------------------------------------------------------------------
@router.get("/services", response_model=List[ServiceStatus])
def get_services(user: Dict[str, Any] = Depends(get_current_user)):
    return query_systemd_services()

@router.post("/services/{service_name}/restart", response_model=GenericResponse)
def restart_service(
    service_name: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    if not is_service_whitelisted(service_name):
        log_audit_event("systemd_restart_denied", service_name, "failure", username=user["username"], ip_address=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Service is not in the authorized whitelist.")

    success, msg = restart_systemd_service(service_name)
    stat = "success" if success else "failure"
    log_audit_event("systemd_restart", service_name, stat, username=user["username"], ip_address=client_ip, details={"message": msg})

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return GenericResponse(success=True, message=msg)

# ------------------------------------------------------------------------------
# Docker Containers
# ------------------------------------------------------------------------------
@router.get("/docker", response_model=List[DockerContainerStatus])
def get_containers(user: Dict[str, Any] = Depends(get_current_user)):
    return query_docker_containers()

@router.post("/docker/{container_name}/restart", response_model=GenericResponse)
def restart_container(
    container_name: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    if not is_container_whitelisted(container_name):
        log_audit_event("docker_restart_denied", container_name, "failure", username=user["username"], ip_address=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Container is not in the authorized whitelist.")

    success, msg = restart_docker_container(container_name)
    stat = "success" if success else "failure"
    log_audit_event("docker_restart", container_name, stat, username=user["username"], ip_address=client_ip, details={"message": msg})

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return GenericResponse(success=True, message=msg)

# ------------------------------------------------------------------------------
# Host Reboot
# ------------------------------------------------------------------------------
@router.post("/reboot", response_model=GenericResponse)
def reboot_host(
    req: HostRebootRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    client_ip = request.client.host if request.client else "unknown"
    if req.confirm_text.strip() != "REBOOT":
        log_audit_event("host_reboot_rejected", "host", "failure", username=user["username"], ip_address=client_ip, details={"reason": "Invalid confirmation phrase"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation phrase mismatch. Please enter 'REBOOT'.")

    log_audit_event("host_reboot_requested", "host", "pending", username=user["username"], ip_address=client_ip)
    success, msg = execute_host_reboot()
    stat = "success" if success else "failure"
    log_audit_event("host_reboot_executed", "host", stat, username=user["username"], ip_address=client_ip, details={"message": msg})

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return GenericResponse(success=True, message=msg)
