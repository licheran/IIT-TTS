"""FastAPI application. `create_app` takes a database URL so tests can use their own."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tts.api.errors import install_error_handlers
from tts.api.routers import datasets, io, results, runs, tables, validate
from tts.store.db import database_url, make_engine, make_session_factory, upgrade


def create_app(url: str | None = None, migrate: bool = True) -> FastAPI:
    db_url = url or database_url()
    engine = make_engine(db_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if migrate:
            upgrade(db_url)
        yield
        engine.dispose()

    app = FastAPI(title="IIT-TTS", lifespan=lifespan)
    app.state.session_factory = make_session_factory(engine)
    install_error_handlers(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(datasets.router)
    app.include_router(tables.router)
    app.include_router(io.router)
    app.include_router(runs.router)
    app.include_router(results.router)
    app.include_router(validate.router)
    return app


app = create_app()
