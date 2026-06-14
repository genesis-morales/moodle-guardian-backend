import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.guardian import router as guardian_router
from src.api.v1.health import router as health_router
from src.api.v1.sync import router as sync_router
from src.api.v1.telegram import router as telegram_router
from src.infrastructure.db.database import Base, engine
from src.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Moodle Guardian API")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database schema ready")
    yield
    logger.info("Shutting down Moodle Guardian API")


app = FastAPI(
    title="Moodle Guardian API",
    version="1.0.0",
    debug=True,
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "moodle-guardian"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guardian_router)
app.include_router(sync_router)
app.include_router(telegram_router, prefix="/v1")
app.include_router(health_router)