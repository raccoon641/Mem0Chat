from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Response

from .config import get_settings
from .database import Base, engine
from .routers import webhook, memories, interactions, analytics


def _twiml(msg: str) -> str:
    safe = (msg or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<Response><Message>{safe}</Message></Response>"


def create_app() -> FastAPI:
    app = FastAPI(title="WhatsApp Memory Assistant")

    # Ensure tables exist (for demo). For real use, prefer migrations.
    Base.metadata.create_all(bind=engine)

    # Root handlers to satisfy Twilio validation or misconfigured callbacks
    @app.get("/")
    def root_get() -> Response:
        return Response(content=_twiml("OK"), media_type="application/xml; charset=utf-8")

    @app.post("/")
    def root_post() -> Response:
        return Response(content=_twiml("OK"), media_type="application/xml; charset=utf-8")

    app.include_router(webhook.router)
    app.include_router(memories.router)
    app.include_router(interactions.router)
    app.include_router(analytics.router)

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True) 