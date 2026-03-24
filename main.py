from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.core.logging import setup_logging
from app.api.v1.router import router as v1_router

FRONTEND_DIR = Path(__file__).parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await engine.dispose()


app = FastAPI(
    title="Job Automation Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.include_router(v1_router, prefix=settings.api_v1_prefix)
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(FRONTEND_DIR / "index.html")
