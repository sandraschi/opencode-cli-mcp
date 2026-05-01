import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.capabilities import router as capabilities_router
from api.routes.proxy import router as proxy_router

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "10951"))

app = FastAPI(
    title="opencode-cli-mcp API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(capabilities_router, prefix="/api")
app.include_router(proxy_router, prefix="/api")


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=BACKEND_PORT)


if __name__ == "__main__":
    main()
