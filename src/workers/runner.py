import asyncio
import logging
from contextlib import suppress

from src.config.logging import setup_logging
from src.infrastructure.db.database import Base, engine
from src.workers.scheduler import build_scheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    logger.info("Ensuring database schema is ready")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema ready")

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