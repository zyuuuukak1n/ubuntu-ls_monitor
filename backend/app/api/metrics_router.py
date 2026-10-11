import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.metrics import collect_system_metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/current")
def get_current_metrics(user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the latest snapshot of server resource and hardware metrics."""
    return collect_system_metrics()

@router.get("/stream")
async def stream_metrics(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Streams system metrics using Server-Sent Events (SSE) every 2 seconds.
    Automatically terminates when the client disconnects.
    """
    async def event_generator():
        try:
            while True:
                # Disconnection check
                if await request.is_disconnected():
                    break

                metrics = collect_system_metrics()
                data = json.dumps(metrics, ensure_ascii=False)
                yield f"data: {data}\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
