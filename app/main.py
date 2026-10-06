from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.payloads import router as payload_router
from app.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Caching Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(payload_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}