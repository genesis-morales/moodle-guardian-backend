from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Moodle Guardian API"
    app_version: str = "1.0.0"

    database_url: str = Field(...)

    @field_validator("database_url")
    @classmethod
    def _force_asyncpg_driver(cls, value: str) -> str:
        # Neon (y casi todos los proveedores) entregan la URL en formato sync
        # `postgresql://`. El motor de la app y Alembic son async, así que
        # normalizamos el driver a asyncpg sin importar cómo venga la URL.
        # Sin esto, SQLAlchemy carga psycopg2 y falla con
        # "The asyncio extension requires an async driver to be used".
        if value.startswith("postgresql+asyncpg://"):
            return value
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value[len("postgresql://") :]
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://") :]
        return value

    moodle_base_url: str = Field(
        default="https://aprende.uned.ac.cr/webservice/rest/server.php"
    )
    moodle_site_info_function: str = "core_webservice_get_site_info"
    moodle_courses_function: str = "core_enrol_get_users_courses"
    moodle_calendar_events_function: str = "core_calendar_get_calendar_events"
    moodle_assignments_function: str = "mod_assign_get_assignments"

    telegram_bot_token: str | None = None
    telegram_api_base_url: str = "https://api.telegram.org"
    request_timeout_seconds: int = 30

    # Token compartido que protege los endpoints de cron (/v1/cron/{job}).
    # Un disparador externo (cron-job.org, UptimeRobot...) debe enviarlo en el
    # header `X-Cron-Token`. Si queda en None, los endpoints de cron responden
    # 503 (deshabilitados) en vez de quedar abiertos sin protección.
    cron_secret_token: str | None = None

    scheduler_interval_hours: int = 3
    scheduler_run_immediately_on_start: bool = False

    # Observabilidad. `sentry_dsn` vacío => Sentry deshabilitado (no-op).
    # `environment` etiqueta los eventos (local/dev/prod) y sirve para el factory
    # de entornos (ver docs/roadmap.md init. 6).
    sentry_dsn: str | None = None
    environment: str = "local"

    # PER-TENANT SEAM: hoy global; a futuro debería vivir por usuario
    # (User.timezone). Ver docs/saas-multitenancy.md.
    # Zona horaria para mostrar fechas en las notificaciones.
    # Moodle entrega los timestamps en UTC; aquí los convertimos a hora local.
    timezone: str = "America/Costa_Rica"

    # Recordatorio "faltan N días": se envía a las reminder_hour (hora local)
    # para las entregas cuya fecha cae exactamente reminder_days_before días después.
    reminder_days_before: int = 3
    reminder_hour: int = 15

    # Digest semanal: día de la semana (lun..dom en formato APScheduler) y hora local.
    digest_weekday: str = "mon"
    digest_hour: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()