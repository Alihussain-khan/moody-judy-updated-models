from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ensure_dirs, settings
from app.core.logging import setup_logging
from app.api.V1.router import router as v1_router

def create_app() -> FastAPI:
    setup_logging()
    ensure_dirs()

    app = FastAPI(title="Moody Judy Backend", version="0.1.0")

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/v1")

    @app.get("/health")
    def health():
        return {"ok": True}

    return app

app = create_app()