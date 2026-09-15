# Per-repo fleet start config for opencode-cli-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'opencode-cli-mcp'
    BackendPort  = 10951
    FrontendPort = 10950
    HealthPath   = '/api/v1/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        # Unified app: REST /api/* + FastMCP /mcp on the same port (api/main.py
        # mounts opencode_cli_mcp.server:http_app at /mcp with its lifespan).
        # NEVER point uvicorn at opencode_cli_mcp.server:app: that is the raw
        # FastMCP object (not ASGI-callable) and every request 500s with
        # "TypeError: 'FastMCP' object is not callable" (seen 2026-09-15).
        UvicornTarget = 'api.main:app'
        Env           = @{
            WEB_PORT = '10951'
            # Dedicated opencode serve port (4097), NOT 4096: the official
            # OpenCode desktop app spawns a password-protected serve on 4096
            # (OPENCODE_SERVER_PASSWORD) that this backend cannot authenticate
            # against. The backend autostarts its own serve on 4097.
            OPENCODE_SERVE_URL = 'http://127.0.0.1:4097'
        }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
