from fastapi import FastAPI

from src.api.v1.guardian import router as guardian_router
from src.api.v1.health import router as health_router
from src.infrastructure.db.database import Base, engine
from src.api.v1.sync import router as sync_router
from src.api.v1.telegram import router as telegram_router

app = FastAPI(title="Moodle Guardian API", version="1.0.0", debug=True)

@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(guardian_router)
app.include_router(sync_router)
app.include_router(telegram_router, prefix="/v1")

app.include_router(health_router)
