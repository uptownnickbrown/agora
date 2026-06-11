from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, demo, fun, instructor, market, student, tutor, ws
from .config import get_settings
from .services.common import GameError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev/SQLite convenience: create the schema in place. Postgres uses alembic.
    settings = get_settings()
    if settings.env in ("dev", "test") and settings.database_url.startswith("sqlite"):
        from .db import Base, make_engine

        engine = make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
    yield


app = FastAPI(title="Agora API", version="0.2.0", lifespan=lifespan)


class CommitBeforeResponse:
    """Commit the request's DB session before the response is sent (see
    deps.current_db_session) so read-after-write is consistent across
    back-to-back requests. Error responses roll back in get_db instead."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and message["status"] < 400:
                from .deps import current_db_session

                session = current_db_session.get()
                if session is not None:
                    await session.commit()
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(CommitBeforeResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")
                   if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GameError)
async def game_error_handler(request: Request, exc: GameError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(student.router)
app.include_router(market.router)
app.include_router(fun.router)
app.include_router(tutor.router)
app.include_router(instructor.router)
app.include_router(ws.router)
app.include_router(admin.router)
app.include_router(demo.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": get_settings().env}
