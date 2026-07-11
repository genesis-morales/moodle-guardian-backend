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
    app_name: str = "CampusGuardian API"
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

    # Canal email vía Brevo (ex-Sendinblue). API HTTP (no SMTP): POST a
    # {brevo_api_base_url}/smtp/email con header `api-key`. El remitente debe ser un
    # dominio/correo verificado en Brevo (deliverability). VACÍOS hasta que el canal
    # se prenda; el email real es opt-in explícito (USE_FAKE_EMAIL=false), NO atado a
    # environment=prod, para no exigir credenciales Brevo donde aún no existen.
    brevo_api_key: str | None = None
    brevo_sender_email: str | None = None
    brevo_sender_name: str = "CampusGuardian"
    brevo_api_base_url: str = "https://api.brevo.com/v3"

    # Override del email real/fake. Análogo a USE_FAKE_NOTIFIER pero con default
    # distinto: el email arranca SIEMPRE fake salvo que se pida real explícito, así
    # sumar el canal no rompe prod (que hoy no tiene BREVO_API_KEY).
    use_fake_email_override: bool | None = Field(
        default=None, validation_alias="USE_FAKE_EMAIL"
    )

    # URL de la web propia donde el usuario regenera su llave de Moodle cuando el
    # token muere; se enlaza en el aviso de "token expirado". VACÍA hasta que la web
    # exista: el aviso degrada a una variante sin link (no manda un link muerto). Se
    # setea por env (WEB_RELINK_URL) cuando la web esté lista, sin tocar código.
    web_relink_url: str = ""

    # Orígenes web autorizados para CORS (separados por coma). El navegador solo
    # deja que la web del usuario llame a esta API si su origen figura aquí. NO usar
    # "*" junto con credenciales: el navegador lo rechaza por spec y deja de proteger.
    # En prod, setear CORS_ALLOWED_ORIGINS con el dominio real de la web
    # (p. ej. "https://guardian.tudominio.com"). El default cubre dev local (Vite/CRA).
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

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

    # Override explícito del notifier real/fake, DESACOPLADO del environment.
    # None (default) => comportamiento histórico: fake salvo en prod. Setear
    # `USE_FAKE_NOTIFIER=false` permite Telegram REAL con Moodle fake en local
    # (probar entregas de digest/reminders/cambios sin pegarle a UNED). El
    # environment sigue decidiendo el Moodle real/fake; solo el notifier se separa.
    use_fake_notifier_override: bool | None = Field(
        default=None, validation_alias="USE_FAKE_NOTIFIER"
    )

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
    def _guard_real_notifier_requires_creds(self) -> "Settings":
        # Fail-fast: si el notifier efectivo es real (prod, o override
        # USE_FAKE_NOTIFIER=false), sin token no puede enviar. Preferimos no
        # arrancar a descubrirlo en el primer envío. Cubre prod y el override.
        if not self.use_fake_notifier and not self.telegram_bot_token:
            raise ValueError(
                "Notifier real (environment='prod' o USE_FAKE_NOTIFIER=false) "
                "requiere TELEGRAM_BOT_TOKEN."
            )
        # Mismo fail-fast para el email real: si se pidió Brevo real (USE_FAKE_EMAIL=
        # false) sin credenciales, no puede enviar. Solo aplica cuando se opta por real.
        if not self.use_fake_email and (
            not self.brevo_api_key or not self.brevo_sender_email
        ):
            raise ValueError(
                "Email real (USE_FAKE_EMAIL=false) requiere BREVO_API_KEY y "
                "BREVO_SENDER_EMAIL."
            )
        return self

    @property
    def use_fake_moodle(self) -> bool:
        return self.environment == "local"

    @property
    def use_fake_notifier(self) -> bool:
        # El override explícito manda; si no está, cae al default por environment
        # (fake salvo en prod). Desacopla el canal de notificación del Moodle.
        if self.use_fake_notifier_override is not None:
            return self.use_fake_notifier_override
        return self.environment != "prod"

    @property
    def use_fake_email(self) -> bool:
        # A diferencia del notifier, el email arranca fake SIEMPRE salvo opt-in
        # explícito (USE_FAKE_EMAIL=false): el canal es nuevo y prod no tiene creds
        # Brevo todavía, así que no debe activarse solo por ser prod.
        if self.use_fake_email_override is not None:
            return self.use_fake_email_override
        return True

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
        # Permite poblar campos con alias (p. ej. use_fake_notifier_override /
        # USE_FAKE_NOTIFIER) tanto por el env var (alias) como por el nombre.
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()