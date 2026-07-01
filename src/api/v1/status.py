"""Endpoint de estado/observabilidad (protegido).

A diferencia de `/v1/health` (liveness barato para pings de uptime, sin tocar la
DB para no impedir el scale-to-zero de Neon), este endpoint hace un chequeo real
de DB y devuelve el historial de corridas del scan. Consulta on-demand, no en
cada ping. Protegido con el mismo `X-Cron-Token` que los jobs de cron.
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, status

from src.api.dependencies import get_scan_run_repository, get_user_repository
from src.config.settings import get_settings
from src.domain.entities.scan_run import ScanRun

router = APIRouter(prefix="/v1/status", tags=["status"])


def _authorize(x_cron_token: str | None) -> None:
    """Protege el endpoint con `CRON_SECRET_TOKEN` (header `X-Cron-Token`).

    Reutilizamos el token que ya tenías configurado. Si no hay token, el endpoint
    responde 503 (fail-closed) para no quedar abierto.
    """
    expected = get_settings().cron_secret_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Status endpoint disabled: CRON_SECRET_TOKEN not configured",
        )
    if not x_cron_token or not secrets.compare_digest(x_cron_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Cron-Token",
        )


def _serialize_run(run: ScanRun, now: datetime) -> dict:
    return {
        "job_name": run.job_name,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat(),
        "age_seconds": int((now - run.finished_at).total_seconds()),
        "duration_ms": run.duration_ms,
        "total_users": run.total_users,
        "success_count": run.success_count,
        "failure_count": run.failure_count,
        "failures": [
            {"moodle_user_id": f.moodle_user_id, "error": f.error}
            for f in run.failures
        ],
    }


@router.get("")
async def get_status(
    limit: int = 20,
    x_cron_token: str | None = Header(default=None),
) -> dict:
    _authorize(x_cron_token)

    now = datetime.now(UTC)
    db_ok = True

    active_users: int | None = None
    try:
        active_users = len(await get_user_repository().list_active())
    except Exception:
        db_ok = False

    runs: list[ScanRun] = []
    try:
        runs = await get_scan_run_repository().list_recent(limit)
    except Exception:
        db_ok = False

    last = runs[0] if runs else None

    return {
        "db": "ok" if db_ok else "error",
        "active_users": active_users,
        "last_scan": _serialize_run(last, now) if last else None,
        "recent_runs": [_serialize_run(run, now) for run in runs],
    }
