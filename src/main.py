from fastapi import FastAPI

from src.api.v1.guardian import router as guardian_router
from src.api.v1.health import router as health_router
from src.infrastructure.db.database import Base, engine
from src.infrastructure.db import models  # noqa: F401

app = FastAPI(title="Moodle Guardian API", version="1.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(guardian_router)
app.include_router(health_router)