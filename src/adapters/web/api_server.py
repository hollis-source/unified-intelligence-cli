from __future__ import annotations

from typing import Awaitable, Callable, Dict, Any, List

from aiohttp import web

# Type alias for dependency injection (Clean Architecture)
TaskRunner = Callable[[List[str]], Awaitable[Dict[str, Any]]]


async def _handle_health(_req: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def _bad_request(message: str) -> web.Response:
    return web.json_response({"error": message}, status=400)


async def _parse_tasks(req: web.Request) -> List[str] | web.Response:
    try:
        body = await req.json()
    except Exception:
        return _bad_request("invalid or missing JSON body")

    tasks = body.get("tasks") if isinstance(body, dict) else None
    if not isinstance(tasks, list) or not tasks or not all(isinstance(t, str) for t in tasks):
        return _bad_request("'tasks' must be a non-empty list of strings")
    return tasks


def create_app(task_runner: TaskRunner) -> web.Application:
    app = web.Application()

    async def handle_tasks(req: web.Request) -> web.Response:
        tasks_or_err = await _parse_tasks(req)
        if isinstance(tasks_or_err, web.Response):
            return tasks_or_err
        try:
            result = await task_runner(tasks_or_err)
            return web.json_response({"ok": True, "result": result})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    app.add_routes([
        web.get("/health", _handle_health),
        web.post("/api/v1/tasks", handle_tasks),
    ])
    return app


def run_server(task_runner: TaskRunner, host: str = "0.0.0.0", port: int = 8080) -> None:
    web.run_app(create_app(task_runner), host=host, port=port)

