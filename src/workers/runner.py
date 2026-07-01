import asyncio
import logging
from contextlib import suppress
from pathlib import Path

from src.config.logging import setup_logging
from src.config.observability import init_sentry
from src.workers.scheduler import build_scheduler

logger = logging.getLogger(__name__)


def add_file_logging() -> None:
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_dir / "worker.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)


async def main() -> None:
    setup_logging()
    add_file_logging()
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