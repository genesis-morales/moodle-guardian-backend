import asyncio
import logging
from contextlib import suppress

from src.config.logging import setup_logging
from src.config.observability import init_sentry
from src.workers.scheduler import build_scheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    # setup_logging() ya instala el RotatingFileHandler sobre logs/worker.log
    # (con rotación y backups). No agregamos un segundo FileHandler: eso
    # duplicaba cada línea del worker en el archivo.
    setup_logging()
    init_sentry()

    # El esquema lo gestiona Alembic (alembic upgrade head); ya no usamos create_all.
    logger.info("Starting scheduler worker")
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler worker started")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Scheduler worker cancellation received")
        raise
    finally:
        logger.info("Shutting down scheduler worker")
        with suppress(Exception):
            scheduler.shutdown(wait=True)
        logger.info("Scheduler worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass