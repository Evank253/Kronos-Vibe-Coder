from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.agents.swarm.task_manager import SwarmTaskManager
from backend.codespace_adapter import dashboard_url, is_codespace, resolve_workspace_path, workspace_root


router = APIRouter(prefix="/vibe", tags=["vibe"])
TASK_MANAGER = SwarmTaskManager()


@router.post("/scan-and-fix")
def scan_and_fix(data: dict[str, Any] | None = None):
    payload = data or {}
    try:
        root_path = resolve_workspace_path(payload.get("path") or workspace_root())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not Path(root_path).exists():
        raise HTTPException(status_code=404, detail="Path not found")
    task = TASK_MANAGER.create_task(str(root_path))
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "codespace": is_codespace(),
        "dashboard_url": dashboard_url(task["task_id"]),
    }


@router.get("/status/{task_id}")
def vibe_status(task_id: str):
    task = TASK_MANAGER.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/merge-results")
def merge_results(data: dict[str, Any]):
    task_id = data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    try:
        return TASK_MANAGER.finalize(task_id, write_files=bool(data.get("write_files")))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.websocket("/updates/{task_id}")
async def vibe_updates(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            task = TASK_MANAGER.get_task(task_id)
            if task is None:
                await websocket.send_json({"task_id": task_id, "status": "missing"})
                return
            await websocket.send_json(task)
            if task["status"] in {"completed", "completed_with_errors", "failed"}:
                return
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        return
