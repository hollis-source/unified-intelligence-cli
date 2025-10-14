from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Dict, Any

from aiohttp import web

from src.core.port.file_store import IFileStore
from src.core.entity.file_ref import FileRef


def _ensure_dir(path: Path) -> None:
    if path and not path.exists():
        path.mkdir(parents=True, exist_ok=True)


async def _handle_health(_req: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _store_text_file(file_store: IFileStore, dst: Path, text: str) -> None:
    ref = FileRef(scheme="file", host=None, path=str(dst))
    await file_store.write(ref, text)


async def _handle_upload(req: web.Request) -> web.Response:
    app = req.app
    file_store: IFileStore = app["file_store"]
    upload_dir: Path = app["upload_dir"]

    reader = await req.multipart()
    stored: List[Dict[str, Any]] = []

    while True:
        part = await reader.next()
        if part is None:
            break
        if part.name != "file" or not part.filename:
            continue
        if not (part.headers.get("Content-Type", "text/plain").startswith("text/")):
            return web.json_response({"error": "only text/* uploads are supported currently"}, status=415)
        data = await part.read()
        text = data.decode("utf-8")
        dst = upload_dir / part.filename
        _ensure_dir(dst.parent)
        await _store_text_file(file_store, dst, text)
        stored.append({"filename": part.filename, "path": str(dst.resolve()), "uri": FileRef(scheme="file", host=None, path=str(dst)).to_uri()})

    return web.json_response({"stored": stored})


def create_app(file_store: IFileStore, upload_dir: Path) -> web.Application:
    app = web.Application()
    app["file_store"] = file_store
    app["upload_dir"] = Path(upload_dir)
    app.add_routes([web.get("/health", _handle_health), web.post("/admin/upload", _handle_upload)])
    return app


def run_server(file_store: IFileStore, upload_dir: Path, host: str = "0.0.0.0", port: int = 8080) -> None:
    web.run_app(create_app(file_store, upload_dir), host=host, port=port)

