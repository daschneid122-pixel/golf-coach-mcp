"""
HTTP entry point for golf-coach MCP.

Imports the FastMCP instance from server.py and exposes it as a streamable-HTTP
ASGI app on PORT (env var, default 8000) with optional Bearer-token auth.

Run locally:
    AUTH_TOKEN=mysecret PORT=8000 python http_server.py

The server.py file remains the stdio entry point for local Claude Desktop use.
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from server import mcp

# Public hostname on Render — disable DNS rebinding protection
# (it's a localhost-only safety, doesn't apply to public servers)
try:
    mcp.settings.transport_security.enable_dns_rebinding_protection = False
except Exception:
    try:
        mcp.settings.transport_security.allowed_hosts = ['*']
    except Exception:
        pass


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token in the Authorization header."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        # Health check is always open — Render uses it for liveness probes.
        if request.url.path == "/health":
            return JSONResponse({"status": "ok"})

        header = request.headers.get("authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix) or header[len(prefix):] != self._token:
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)


def build_app():
    """Build the ASGI app with optional Bearer-token middleware."""
    app = mcp.streamable_http_app()

    # Add a /health endpoint that bypasses auth.
    async def health(_request: Request) -> Response:
        return JSONResponse({"status": "ok", "server": "golf-coach"})

    # Starlette apps allow appending routes after construction.
    app.router.routes.append(
        # Lazy import so we don't pull starlette.routing at top level.
        __import__("starlette.routing", fromlist=["Route"]).Route(
            "/health", health, methods=["GET"]
        )
    )

    auth_token = os.getenv("AUTH_TOKEN")
    if auth_token:
        app.add_middleware(BearerAuthMiddleware, token=auth_token)

    return app


# Module-level app for ASGI servers (uvicorn / gunicorn workers can import this).
app = build_app()


def main() -> None:
    """Entry point: run with uvicorn on PORT (default 8000)."""
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    if not os.getenv("AUTH_TOKEN"):
        print(
            "WARNING: AUTH_TOKEN not set. Server will be PUBLIC. "
            "Set AUTH_TOKEN=<long-random-string> before deploying.",
            flush=True,
        )

    uvicorn.run(app, host=host, port=port, log_level=os.getenv("LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()
