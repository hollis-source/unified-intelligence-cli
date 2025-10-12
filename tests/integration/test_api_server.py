import asyncio
from typing import List, Dict, Any, Tuple

import aiohttp
import pytest
from aiohttp import web

# TDD: import will fail until implemented
from src.adapters.web.api_server import create_app  # type: ignore


async def _start_app(app: web.Application) -> Tuple[web.AppRunner, int]:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    # type: ignore[attr-defined]
    sockets = list(site._server.sockets)  
    port = sockets[0].getsockname()[1]
    return runner, port


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    async def dummy_runner(tasks: List[str]) -> Dict[str, Any]:
        return {"echo": tasks}

    app = create_app(task_runner=dummy_runner)
    runner, port = await _start_app(app)
    try:
        base = f"http://127.0.0.1:{port}"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base}/health") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "ok"
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_post_tasks_runs_runner_and_returns_result():
    async def dummy_runner(tasks: List[str]) -> Dict[str, Any]:
        # Simulate minimal async processing
        await asyncio.sleep(0)
        return {"handled": len(tasks), "tasks": tasks}

    app = create_app(task_runner=dummy_runner)
    runner, port = await _start_app(app)
    try:
        base = f"http://127.0.0.1:{port}"
        payload = {"tasks": ["one", "two"]}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base}/api/v1/tasks", json=payload) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["ok"] is True
                assert data["result"]["handled"] == 2
                assert data["result"]["tasks"] == ["one", "two"]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_post_tasks_validates_input():
    async def dummy_runner(tasks: List[str]) -> Dict[str, Any]:
        return {"tasks": tasks}

    app = create_app(task_runner=dummy_runner)
    runner, port = await _start_app(app)
    try:
        base = f"http://127.0.0.1:{port}"
        async with aiohttp.ClientSession() as session:
            # Missing body
            async with session.post(f"{base}/api/v1/tasks") as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "error" in data

            # Invalid type
            async with session.post(f"{base}/api/v1/tasks", json={"tasks": "not-a-list"}) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "error" in data

            # Empty list
            async with session.post(f"{base}/api/v1/tasks", json={"tasks": []}) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "error" in data
    finally:
        await runner.cleanup()

