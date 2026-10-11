import asyncio
import subprocess
import shutil
import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.system_control import is_service_whitelisted, is_container_whitelisted

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("/systemd/{service_name}/stream")
async def stream_systemd_logs(
    service_name: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    if not is_service_whitelisted(service_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{service_name}' is not in the authorized whitelist."
        )

    has_journalctl = shutil.which("journalctl") is not None

    async def log_generator():
        if not has_journalctl:
            # Simulated logs for dev environment
            yield f"data: {json.dumps({'line': f'[DEV] Simulated journal log for {service_name}'})}\n\n"
            for i in range(1, 10):
                if await request.is_disconnected():
                    break
                await asyncio.sleep(2)
                yield f"data: {json.dumps({'line': f'[DEV] Sample systemd event {i} for {service_name}'})}\n\n"
            return

        cmd = ["journalctl", "-u", service_name, "-n", "100", "-f", "--no-pager"]
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                if await request.is_disconnected():
                    break

                line = await proc.stdout.readline()
                if not line:
                    break

                text = line.decode("utf-8", errors="replace").rstrip()
                data = json.dumps({"line": text}, ensure_ascii=False)
                yield f"data: {data}\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    proc.kill()

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/docker/{container_name}/stream")
async def stream_docker_logs(
    container_name: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    if not is_container_whitelisted(container_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Container '{container_name}' is not in the authorized whitelist."
        )

    has_docker = shutil.which("docker") is not None

    async def docker_log_generator():
        if not has_docker:
            yield f"data: {json.dumps({'line': f'[DEV] Simulated container log for {container_name}'})}\n\n"
            for i in range(1, 10):
                if await request.is_disconnected():
                    break
                await asyncio.sleep(2)
                yield f"data: {json.dumps({'line': f'[DEV] Container output line {i} for {container_name}'})}\n\n"
            return

        cmd = ["docker", "logs", "-n", "100", "-f", container_name]
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                if await request.is_disconnected():
                    break

                line = await proc.stdout.readline()
                if not line:
                    break

                text = line.decode("utf-8", errors="replace").rstrip()
                data = json.dumps({"line": text}, ensure_ascii=False)
                yield f"data: {data}\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    proc.kill()

    return StreamingResponse(
        docker_log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
