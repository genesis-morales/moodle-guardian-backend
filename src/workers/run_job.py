"""Entrypoint one-shot para correr un job programado una sola vez y salir.

Pensado para disparadores externos (p. ej. GitHub Actions cron) que ejecutan el
job y terminan el proceso, en vez de mantener vivo el scheduler de APScheduler
(`runner.py`). La lógica de negocio es la misma; esto solo reemplaza la capa de
disparo.

Uso:
    python -m src.workers.run_job {scan|reminders|digest}
"""

import asyncio
import logging
import sys

from src.config.logging import setup_logging
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.workers.jobs.send_deadline_reminders import send_deadline_reminders_job
from src.workers.jobs.send_monday_digest import send_monday_digest_job

logger = logging.getLogger(__name__)

JOBS = {
    "scan": scan_all_users_job,
    "reminders": send_deadline_reminders_job,
    "digest": send_monday_digest_job,
}


def main() -> None:
    setup_logging()

    if len(sys.argv) != 2 or sys.argv[1] not in JOBS:
        logger.error(
            "Uso: python -m src.workers.run_job {%s}", "|".join(JOBS)
        )
        raise SystemExit(2)

    name = sys.argv[1]
    logger.info("Running job '%s' (one-shot)", name)
    asyncio.run(JOBS[name]())
    logger.info("Job '%s' finished", name)


if __name__ == "__main__":
    main()
