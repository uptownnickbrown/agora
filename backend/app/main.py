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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
