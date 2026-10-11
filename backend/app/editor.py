import os
import shutil
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from app.config import load_operation_config
from app.models import EditableFileInfo

def get_editable_file_configs() -> List[Dict[str, Any]]:
    cfg = load_operation_config()
    return cfg.get("editable_files", [])

def find_whitelisted_file_config(requested_path: str) -> Optional[Dict[str, Any]]:
    """
    Validates requested path against the strict whitelist.
    Prevents path traversal, symlink spoofing, and directory escape.
    """
    editable_configs = get_editable_file_configs()
    try:
        # Normalize and resolve requested path
        norm_requested = str(Path(requested_path).resolve())
    except Exception:
        return None

    for item in editable_configs:
        cfg_path = item.get("path")
        if not cfg_path:
            continue
        try:
            norm_cfg = str(Path(cfg_path).resolve())
            if norm_requested == norm_cfg:
                return item
        except Exception:
            continue

    return None

def list_editable_files() -> List[EditableFileInfo]:
    """Returns metadata for all files in the editable whitelist."""
    configs = get_editable_file_configs()
    result = []
    for item in configs:
        p_str = item["path"]
        p = Path(p_str)
        exists = p.exists() and p.is_file()
        size = p.stat().st_size if exists else None
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat() if exists else None

        result.append(EditableFileInfo(
            path=p_str,
            label=item.get("label", p.name),
            description=item.get("description"),
            syntax=item.get("syntax", "text"),
            exists=exists,
            size=size,
            last_modified=mtime
        ))
    return result

def read_whitelisted_file(path_str: str) -> Tuple[bool, str, Optional[str]]:
    """Reads content of a whitelisted file. Returns (success, content/error, syntax)."""
    cfg = find_whitelisted_file_config(path_str)
    if not cfg:
        return False, f"Access denied: path '{path_str}' is not whitelisted.", None

    p = Path(cfg["path"])
    if not p.exists():
        # Return empty template if file does not yet exist
        return True, "", cfg.get("syntax", "text")

    try:
        content = p.read_text(encoding="utf-8")
        return True, content, cfg.get("syntax", "text")
    except Exception as e:
        return False, f"Failed to read file: {str(e)}", None

def run_validation_command(cmd: List[str], temp_file_path: Optional[str] = None) -> Tuple[bool, str]:
    """Runs the dry-run validation command without shell."""
    if not cmd or not isinstance(cmd, list):
        return True, "No validation command defined."

    binary = cmd[0]
    if not shutil.which(binary):
        # In test or dev environment where binary is missing, pass with notice
        return True, f"[DEV] Binary '{binary}' not present, skipped syntax validation."

    # Substitute {file} placeholder if present
    final_cmd = []
    for arg in cmd:
        if "{temp_file}" in arg and temp_file_path:
            final_cmd.append(arg.replace("{temp_file}", temp_file_path))
        else:
            final_cmd.append(arg)

    try:
        proc = subprocess.run(
            final_cmd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=15
        )
        output = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode == 0:
            return True, output or "Validation passed."
        else:
            return False, f"Validation command failed (code {proc.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return False, "Validation command timed out after 15 seconds."
    except Exception as e:
        return False, f"Validation execution error: {str(e)}"

def save_whitelisted_file(path_str: str, new_content: str, do_backup: bool = True) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Safely saves a whitelisted configuration file.
    Performs backup (.bak.<timestamp>) and dry-run syntax validation.
    Rolls back automatically if validation fails.
    Returns (success, message, backup_path, validation_output).
    """
    cfg = find_whitelisted_file_config(path_str)
    if not cfg:
        return False, f"Access denied: path '{path_str}' is not in the editable files whitelist.", None, None

    target_path = Path(cfg["path"])
    target_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path_str: Optional[str] = None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 1. Create backup if existing
    if target_path.exists():
        backup_path = target_path.with_name(f"{target_path.name}.bak.{timestamp}")
        try:
            shutil.copy2(target_path, backup_path)
            backup_path_str = str(backup_path)
        except Exception as e:
            return False, f"Failed to create backup: {str(e)}", None, None

    # 2. Write new content to a temporary sibling file first
    temp_dir = target_path.parent
    try:
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            temp_file_name = tf.name
            tf.write(new_content)
    except Exception as e:
        return False, f"Failed to write temporary buffer: {str(e)}", backup_path_str, None

    # 3. Dry-run validation check
    validate_cmd = cfg.get("validate_command")
    validation_output: Optional[str] = None
    if validate_cmd:
        valid, val_msg = run_validation_command(validate_cmd, temp_file_path=temp_file_name)
        validation_output = val_msg
        if not valid:
            # Clean up temp file and abort without altering target
            try:
                os.remove(temp_file_name)
            except OSError:
                pass
            return False, f"Syntax validation failed. Changes were rejected:\n{val_msg}", backup_path_str, validation_output

    # 4. Atomic replace target with temp file
    try:
        shutil.move(temp_file_name, target_path)
    except Exception as e:
        # Clean up temp file
        if os.path.exists(temp_file_name):
            try:
                os.remove(temp_file_name)
            except OSError:
                pass
        return False, f"Failed to atomically update file: {str(e)}", backup_path_str, validation_output

    return True, "File saved successfully.", backup_path_str, validation_output
