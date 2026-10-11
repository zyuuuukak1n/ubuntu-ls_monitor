from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status

from app.auth import get_current_user
from app.audit_log import log_audit_event
from app.models import (
    EditableFileInfo,
    FileContentRequest,
    FileSaveRequest,
    FileSaveResponse
)
from app.editor import (
    list_editable_files,
    read_whitelisted_file,
    save_whitelisted_file,
    find_whitelisted_file_config
)

router = APIRouter(prefix="/api/editor", tags=["editor"])

@router.get("/files", response_model=List[EditableFileInfo])
def get_files(user: Dict[str, Any] = Depends(get_current_user)):
    """Lists all files authorized for web viewing and editing."""
    return list_editable_files()

@router.post("/file")
def get_file_content(
    req: FileContentRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves file content if the path matches the strict whitelist."""
    client_ip = request.client.host if request.client else "unknown"
    success, content_or_err, syntax = read_whitelisted_file(req.path)
    if not success:
        log_audit_event("file_read_denied", req.path, "failure", username=user["username"], ip_address=client_ip, details={"reason": content_or_err})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=content_or_err)

    return {
        "path": req.path,
        "content": content_or_err,
        "syntax": syntax or "text"
    }

@router.post("/save", response_model=FileSaveResponse)
def save_file(
    req: FileSaveRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Saves new file content with automatic backup and dry-run syntax verification.
    Rejects any unwhitelisted path or validation error.
    """
    client_ip = request.client.host if request.client else "unknown"

    cfg = find_whitelisted_file_config(req.path)
    if not cfg:
        log_audit_event("file_save_denied", req.path, "failure", username=user["username"], ip_address=client_ip, details={"reason": "Path not in whitelist"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File path is not in the authorized whitelist.")

    success, msg, backup_path, validation_output = save_whitelisted_file(
        path_str=req.path,
        new_content=req.content,
        do_backup=req.backup
    )

    stat = "success" if success else "failure"
    log_audit_event(
        action="file_save",
        target=req.path,
        status=stat,
        username=user["username"],
        ip_address=client_ip,
        details={
            "backup_path": backup_path,
            "validation_output": validation_output,
            "message": msg
        }
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    return FileSaveResponse(
        success=True,
        message=msg,
        backup_path=backup_path,
        validation_output=validation_output
    )
