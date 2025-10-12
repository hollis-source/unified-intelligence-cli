import asyncio
import tempfile
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web

from src.adapters.files import LocalBackend, UnifiedFileStore

# Import will fail initially (TDD) until implementation exists
from src.adapters.web.upload_server import create_app  # type: ignore


async def _start_app(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = list(site._server.sockets)  # type: ignore[attr-defined]
    port = sockets[0].getsockname()[1]
    return runner, port


@pytest.mark.asyncio
async def test_health_and_upload_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        upload_dir = Path(tmp) / "uploads"
        file_store = UnifiedFileStore([LocalBackend()])
        app = create_app(file_store, upload_dir)

        runner, port = await _start_app(app)
        try:
            base = f"http://127.0.0.1:{port}"

            # Health check
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base}/health") as resp:
                    assert resp.status == 200
                    data = await resp.json()
                    assert data["status"] == "ok"

            # Upload a small file
            payload = aiohttp.FormData()
            payload.add_field(
                name="file",
                value=b"hello world",
                filename="hello.txt",
                content_type="text/plain",
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{base}/admin/upload", data=payload) as resp:
                    assert resp.status == 200
                    result = await resp.json()
                    assert "stored" in result and len(result["stored"]) == 1
                    stored_path = Path(result["stored"][0]["path"])  # type: ignore[index]

            # Verify file persisted to disk
            assert stored_path.exists()
            assert stored_path.read_text() == "hello world"
        finally:
            await runner.cleanup()

