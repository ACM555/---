from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assistant, audit, auth, health, legal, platform
from app.core.config import settings
from app.database import init_database
from app.services.legal_seed import seed_legal_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    settings.ensure_dirs()
    init_database()
    seed_legal_sources()
    yield

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

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(legal.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": settings.APP_NAME, "docs": "/docs" if settings.DEBUG else ""}
