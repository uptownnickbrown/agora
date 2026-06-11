from fastapi import FastAPI

from .config import get_settings

app = FastAPI(title="Agora API", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": get_settings().env}


# Real routers (auth, markets, student, instructor) land with Phase 0 proper.
# The economy engine they will wrap lives in app/engine/ and is already
# exercised by the sim harness (backend/sim/) and the test suite.
