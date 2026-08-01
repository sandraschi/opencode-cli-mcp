import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import logs
from api.routes.capabilities import router as capabilities_router
from api.routes.chat import router as chat_router
from api.routes.docs import router as docs_router
from api.routes.fleet import router as fleet_router
from api.routes.logs import router as logs_router
from api.routes.opencode_config import router as opencode_config_router
from api.routes.opencode_tools import router as opencode_tools_router
from api.routes.proxy import router as proxy_router
from api.routes.settings import router as settings_router
from api.routes.system import router as system_router
from api.routes.tools import router as tools_router
from opencode_cli_mcp.server import mcp_app as mcp_http_app

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "10951"))

_allow_origin_regex = r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$"

app = FastAPI(
    title="opencode-cli-mcp API",
    version="0.2.3",
    docs_url="/docs",
    redoc_url="/redoc",
    # The FastMCP StreamableHTTPSessionManager needs its lifespan wired into
    # the parent app, or every /mcp request fails with "task group was not
    # initialized" (gofastmcp.com/deployment/asgi).
    lifespan=mcp_http_app.lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:10950",
        "http://localhost:10950",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    """Capture API traffic into the ring buffer for the Logs page."""
    start = time.monotonic()
    try:
        response = await call_next(request)
        status = response.status_code
        level = "INFO" if status < 400 else "WARNING" if status < 500 else "ERROR"
        logs.log(
            level,
            "api",
            f"{request.method} {request.url.path} -> {status}",
            status=status,
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )
        return response
    except Exception as exc:  # never break the request path for logging
        logs.log("ERROR", "api", f"{request.method} {request.url.path} -> exception: {exc}")
        raise


app.include_router(capabilities_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(docs_router, prefix="/api")
app.include_router(fleet_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(opencode_config_router, prefix="/api")
app.include_router(opencode_tools_router, prefix="/api")
app.include_router(proxy_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(tools_router, prefix="/api")

# Unified surface: the FastMCP Streamable HTTP endpoint lives at /mcp on the
# SAME port as the REST API. One backend process serves both the webapp
# (/api/*) and MCP clients (/mcp). This is the single entry point used by
# run_server.py (PyInstaller/NSIS) and the dev start config.
#
# Mounted at "/" (not "/mcp"): FastMCP's http_app() already routes its
# Streamable HTTP endpoint at /mcp, so mounting at /mcp would double-prefix
# it to /mcp/mcp and break every client configured with the documented URL.
# The FastAPI routes (/api/*, /docs, /openapi.json) are registered before the
# mount and match first; everything else falls through to the MCP app.
app.mount("/", mcp_http_app)


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=BACKEND_PORT)


if __name__ == "__main__":
    main()
