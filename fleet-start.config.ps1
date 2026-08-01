# Per-repo fleet start config for opencode-cli-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'opencode-cli-mcp'
    BackendPort  = 10951
    FrontendPort = 10950
    HealthPath   = '/api/v1/health'
    WebRoot      = 'D:\Dev\repos\opencode-cli-mcp\web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        # Unified app: REST /api/* + FastMCP /mcp on the same port (api/main.py
        # mounts opencode_cli_mcp.server:http_app at /mcp with its lifespan).
        UvicornTarget = 'api.main:app'
        Env           = @{ WEB_PORT = '10951' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
