"""Endpoints HTTP para disparar los jobs programados desde un cron externo.

Pensado para reemplazar los workflows de GitHub Actions (que omiten/retrasan
ejecuciones) por un disparador HTTP fiable como cron-job.org o UptimeRobot,
apuntando a la API ya desplegada en Render.

Cada endpoint corre EXACTAMENTE el mismo job que `python -m src.workers.run_job`
(misma lógica de negocio); esto solo cambia la capa de disparo a HTTP.

Protección: el llamador debe enviar el header `X-Cron-Token` con el valor de
`CRON_SECRET_TOKEN`. Si el token no está configurado en el servidor, los
endpoints responden 503 para no quedar abiertos.
"""

import logging
import secrets

from fastapi import APIRouter, Header, HTTPException, status

from src.config.settings import get_settings
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.workers.jobs.send_deadline_reminders import send_deadline_reminders_job
from src.workers.jobs.send_monday_digest import send_monday_digest_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/cron", tags=["cron"])

JOBS = {
    "scan": scan_all_users_job,
    "reminders": send_deadline_reminders_job,
    "digest": send_monday_digest_job,
}


def _authorize(x_cron_token: str | None) -> None:
    expected = get_settings().cron_secret_token
    if not expected:
        # Sin token configurado preferimos fallar cerrado: el endpoint no opera.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cron endpoints disabled: CRON_SECRET_TOKEN not configured",
        )
    # Comparación en tiempo constante para no filtrar el token por timing.
    if not x_cron_token or not secrets.compare_digest(x_cron_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Cron-Token",
        )


@router.post("/{job}", status_code=status.HTTP_200_OK)
async def run_cron_job(
    job: str,
    x_cron_token: str | None = Header(default=None),
) -> dict:
    _authorize(x_cron_token)

    runner = JOBS.get(job)
    if runner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown job '{job}'. Valid: {', '.join(JOBS)}",
        )

    logger.info("Running job '%s' via HTTP cron trigger", job)
    await runner()
    logger.info("Job '%s' finished (HTTP cron trigger)", job)

    return {"status": "ok", "job": job}
