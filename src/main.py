import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.guardian import router as guardian_router
from src.api.v1.health import router as health_router
from src.api.v1.plans import router as plans_router
from src.api.v1.status import router as status_router
from src.api.v1.sync import router as sync_router
from src.api.v1.telegram import router as telegram_router
from src.config.logging import setup_logging
from src.config.observability import init_sentry
from src.config.settings import get_settings

setup_logging()
init_sentry()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log visible del perfil activo: hace obvio si algo quedó mal configurado
    # (p. ej. ENVIRONMENT sin setear en prod usaría fakes).
    settings = get_settings()
    logger.warning(
        "Starting CampusGuardian API | perfil=%s (moodle=%s, notifier=%s)",
        settings.environment,
        "fake" if settings.use_fake_moodle else "real",
        "fake" if settings.use_fake_notifier else "real",
    )
    # El esquema lo gestiona Alembic (alembic upgrade head). Ya no usamos
    # create_all para que no se adelante a las migraciones.
    yield
    logger.info("Shutting down CampusGuardian API")


app = FastAPI(
    title="CampusGuardian API",
    version="1.0.0",
    debug=True,
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "campusguardian"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guardian_router)
app.include_router(plans_router)
app.include_router(sync_router)
app.include_router(telegram_router, prefix="/v1")
app.include_router(health_router)
app.include_router(status_router)