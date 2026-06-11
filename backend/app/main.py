from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth, fun, instructor, market, student, tutor
from .config import get_settings
from .services.common import GameError

app = FastAPI(title="Agora API", version="0.2.0")

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": get_settings().env}
