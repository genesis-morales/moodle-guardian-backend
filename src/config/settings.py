from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Perfiles de entorno soportados. Cada uno decide, en el composition root
# (src/api/dependencies.py), qué implementaciones se arman:
#   local -> Moodle fake + notifier fake   (desarrollo sin tocar servicios reales)
#   dev   -> Moodle real + notifier fake    (probar contra Moodle real sin spamear usuarios)
#   prod  -> Moodle real + notifier real
_VALID_ENVIRONMENTS = frozenset({"local", "dev", "prod"})


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

    # URL de la web propia donde el usuario regenera su llave de Moodle cuando el
    # token muere; se enlaza en el aviso de "token expirado". VACÍA hasta que la web
    # exista: el aviso degrada a una variante sin link (no manda un link muerto). Se
    # setea por env (WEB_RELINK_URL) cuando la web esté lista, sin tocar código.
    web_relink_url: str = ""

    # Clave(s) Fernet para cifrar el `moodle_token` at-rest (ver
    # src/infrastructure/security/token_cipher.py). Acepta varias separadas por
    # coma para rotación: la PRIMERA cifra, todas descifran. Generar con:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str | None = None

    @property
    def token_encryption_keys(self) -> list[str]:
        if not self.token_encryption_key:
            return []
        return [k.strip() for k in self.token_encryption_key.split(",") if k.strip()]

    # Token compartido que protege los endpoints de cron (/v1/cron/{job}).
    # Un disparador externo (cron-job.org, UptimeRobot...) debe enviarlo en el
    # header `X-Cron-Token`. Si queda en None, los endpoints de cron responden
    # 503 (deshabilitados) en vez de quedar abiertos sin protección.
    cron_secret_token: str | None = None

    scheduler_interval_hours: int = 3
    scheduler_run_immediately_on_start: bool = False

    # Corridas consecutivas del scan con MoodleTokenError que se toleran antes de
    # desactivar+avisar al usuario. Evita que un bache transitorio de Moodle
    # (como el que devolvió `invalidtoken` para tokens sanos) baje a un usuario:
    # el fallo debe persistir a lo largo de N ciclos (default 3 = ~9h a 3h/ciclo).
    # Un scan exitoso resetea el contador.
    token_failure_threshold: int = 3

    # Observabilidad. `sentry_dsn` vacío => Sentry deshabilitado (no-op).
    # `environment` etiqueta los eventos y decide el perfil del factory de
    # entornos (ver docs/roadmap.md init. 6 y _VALID_ENVIRONMENTS arriba).
    sentry_dsn: str | None = None
    environment: str = "local"

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        # Rechazamos valores desconocidos: un typo (ej. "production") no debe
        # degradar silenciosamente a otro perfil y, p.ej., usar fakes en prod.
        normalized = value.strip().lower()
        if normalized not in _VALID_ENVIRONMENTS:
            raise ValueError(
                f"environment='{value}' inválido; usar uno de {sorted(_VALID_ENVIRONMENTS)}."
            )
        return normalized

    @model_validator(mode="after")
    def _guard_prod_requires_notifier_creds(self) -> "Settings":
        # Fail-fast: en prod el notifier es real y sin token no puede enviar.
        # Preferimos no arrancar a descubrirlo en el primer envío.
        if self.environment == "prod" and not self.telegram_bot_token:
            raise ValueError(
                "environment='prod' requiere TELEGRAM_BOT_TOKEN (el notifier real lo necesita)."
            )
        return self

    @property
    def use_fake_moodle(self) -> bool:
        return self.environment == "local"

    @property
    def use_fake_notifier(self) -> bool:
        return self.environment != "prod"

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