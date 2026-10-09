"""College RAG FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import documents, health, stats
from app.core.config import get_settings
from app.database.mongo import close_mongo, init_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_mongo()
    documents.ensure_indexes()
    yield
    close_mongo()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def upload_size_guard(request: Request, call_next):
        upload_path = f"{settings.api_prefix}/documents"
        if request.method == "POST" and request.url.path.rstrip("/") == upload_path:
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit():
                margin = 64 * 1024
                if int(content_length) > settings.max_upload_size_bytes + margin:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"The file exceeds the maximum upload size of "
                                f"{settings.max_upload_size_mb} MB."
                            )
                        },
                    )
        response = await call_next(request)
        return response

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(stats.router, prefix=settings.api_prefix)

    return app


app = create_app()
