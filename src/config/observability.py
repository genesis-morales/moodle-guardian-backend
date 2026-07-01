"""Inicialización de Sentry (error tracking + alertas).

No-op si `SENTRY_DSN` no está configurado, y tolerante a que el paquete no esté
instalado (para que tests/local sin la dependencia no rompan). La integración de
logging de Sentry captura automáticamente los `logger.exception(...)` (nivel
ERROR) de los jobs, así que no hace falta acoplar el código a Sentry.
"""

import logging
import sys

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_initialized = False


def init_sentry() -> None:
    global _initialized
    if _initialized:
        return

    # Bajo pytest no inicializamos Sentry: los tests no deben ensuciar el
    # tracking real con eventos de prueba (pytest siempre está en sys.modules
    # durante los tests, y nunca en los runs reales de uvicorn/scheduler).
    if "pytest" in sys.modules:
        return

    settings = get_settings()
    dsn = settings.sentry_dsn
    if not dsn:
        logger.info("Sentry deshabilitado (sin SENTRY_DSN)")
        return

    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN configurado pero sentry-sdk no está instalado")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        # Solo errores por ahora (sin performance tracing) para no gastar cuota.
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    _initialized = True
    logger.info("Sentry inicializado (environment=%s)", settings.environment)
