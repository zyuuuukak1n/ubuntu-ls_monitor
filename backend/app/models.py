from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# WebAuthn & Auth Schemas
# ------------------------------------------------------------------------------
class RegisterOptionsRequest(BaseModel):
    invite_token: str = Field(..., min_length=16, max_length=128)
    username: str = Field(..., min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_\-\.]+$")

class AddCredentialOptionsRequest(BaseModel):
    name: Optional[str] = Field(default="Passkey", max_length=64)

class RegisterVerifyRequest(BaseModel):
    challenge: str = Field(...)
    response: Dict[str, Any] = Field(...)
    credential_name: Optional[str] = Field(default="Default Passkey", max_length=64)

class LoginOptionsRequest(BaseModel):
    username: Optional[str] = Field(default=None, max_length=32)

class LoginVerifyRequest(BaseModel):
    challenge: str = Field(...)
    response: Dict[str, Any] = Field(...)

class UserInfoResponse(BaseModel):
    id: str
    username: str
    created_at: str

class CredentialInfo(BaseModel):
    id: str
    name: str
    sign_count: int
    transports: Optional[List[str]] = None
    created_at: str
    last_used_at: Optional[str] = None

class RenameCredentialRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

# ------------------------------------------------------------------------------
# System & Service Schemas
# ------------------------------------------------------------------------------
class ServiceStatus(BaseModel):
    name: str
    description: str
    active_state: str  # active, inactive, failed, etc.
    sub_state: str
    load_state: str
    main_pid: Optional[int] = None
    uptime: Optional[str] = None

class DockerContainerStatus(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    created: str
    ports: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_usage: Optional[str] = None

class ServiceRestartRequest(BaseModel):
    service_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.@]+$")

class DockerRestartRequest(BaseModel):
    container_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.]+$")

class HostRebootRequest(BaseModel):
    confirm_text: str = Field(...)

class PortInfo(BaseModel):
    port: int
    proto: str
    address: str
    status: str
    process_name: Optional[str] = None
    pid: Optional[int] = None

class PortOverviewResponse(BaseModel):
    used_ports: List[PortInfo]
    suggested_port: int
    common_ranges: List[Dict[str, Any]]

# ------------------------------------------------------------------------------
# Editor Schemas
# ------------------------------------------------------------------------------
class EditableFileInfo(BaseModel):
    path: str
    label: str
    description: Optional[str] = None
    syntax: str
    exists: bool
    size: Optional[int] = None
    last_modified: Optional[str] = None

class FileContentRequest(BaseModel):
    path: str

class FileSaveRequest(BaseModel):
    path: str
    content: str
    backup: bool = True

class FileSaveResponse(BaseModel):
    success: bool
    message: str
    backup_path: Optional[str] = None
    validation_output: Optional[str] = None

# ------------------------------------------------------------------------------
# Generic Response
# ------------------------------------------------------------------------------
class GenericResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
