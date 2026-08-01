"""PyInstaller entry point — starts the HTTP/uvicorn backend.

Port resolution order matches what native/src/backend.rs actually sets
(OPENCODE_CLI_MCP_PORT); BACKEND_PORT matches api.main's dev-mode env.
Default 10951 is this repo's registered backend port — 10700 belongs to
virtualization-mcp and must never be used here.
"""

import os
import sys

sys.path.insert(0, ".")

import uvicorn

from api.main import app

port = int(os.getenv("OPENCODE_CLI_MCP_PORT") or os.getenv("BACKEND_PORT") or "10951")
host = os.getenv("OPENCODE_CLI_MCP_HOST") or os.getenv("MCP_HOST", "127.0.0.1")
uvicorn.run(app, host=host, port=port, log_level="info")
