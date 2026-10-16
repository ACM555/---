from contextlib import asynccontextmanager
import asyncio
from contextlib import suppress
import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import assistant, audit, auth, health, legal, platform
from app.core.config import settings
from app.database import init_database
from app.services.legal_seed import seed_legal_sources
from app.services.official_monitoring import init_monitoring_database, monitoring_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    settings.ensure_dirs()
    init_database()
    seed_legal_sources()
    init_monitoring_database()
    monitor = asyncio.create_task(monitoring_scheduler()) if settings.MONITORING_ENABLED else None
    try:
        yield
    finally:
        if monitor:
            monitor.cancel()
            with suppress(asyncio.CancelledError):
                await monitor

app = FastAPI(
    title=settings.APP_NAME,
    description="东盟跨境商事法律 AI 助手后端接口",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(legal.router, prefix="/api")


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

mimetypes.add_type("image/webp", ".webp")

if FRONTEND_ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="frontend-assets")


@app.get("/", include_in_schema=False)
async def root():
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-store"})
    return {"message": settings.APP_NAME, "docs": "/docs" if settings.DEBUG else ""}


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    dist_root = FRONTEND_DIST.resolve()
    candidate = (dist_root / path).resolve()
    try:
        candidate.relative_to(dist_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not Found") from exc

    if candidate.is_file():
        return FileResponse(candidate)

    index = dist_root / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-store"})
    raise HTTPException(status_code=404, detail="Frontend build not found")
