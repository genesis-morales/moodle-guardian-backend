import logging
from datetime import UTC, datetime

from src.api.dependencies import (
    get_run_guardian_scan_use_case,
    get_scan_run_repository,
    get_telegram_message_builder,
    get_telegram_notifier,
    get_user_repository,
)
from src.config.settings import get_settings
from src.domain.entities.scan_run import ScanFailure, ScanRun
from src.domain.exceptions.domain_errors import MoodleTokenError

logger = logging.getLogger(__name__)


async def scan_all_users_job() -> None:
    logger.info("Starting scheduled scan for active users")

    user_repository = get_user_repository()
    run_guardian_scan_use_case = get_run_guardian_scan_use_case()
    notifier = get_telegram_notifier()
    message_builder = get_telegram_message_builder()
    web_relink_url = get_settings().web_relink_url

    users = await user_repository.list_active()
    logger.info("Loaded active users for scheduled scan count=%s", len(users))

    started_at = datetime.now(UTC)
    success_count = 0
    failure_count = 0
    failures: list[ScanFailure] = []

    for user in users:
        try:
            logger.info(
                "Running scheduled scan for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )
            await run_guardian_scan_use_case.execute(user.moodle_user_id)
            success_count += 1
        except MoodleTokenError as exc:
            # Token inválido/expirado: no se arregla reintentando. Desactivamos
            # al usuario para sacarlo del loop (si no, falla en CADA corrida cada
            # 3 h ensuciando logs/Sentry). Reactivar requiere re-vincular el
            # token. Logueamos en WARNING (sin traceback) para no generar evento
            # en Sentry por algo esperado y accionable por el usuario.
            failure_count += 1
            failures.append(
                ScanFailure(
                    moodle_user_id=user.moodle_user_id,
                    error=f"MoodleTokenError (usuario desactivado): {exc}"[:500],
                )
            )
            # Avisar al usuario que su token murió (antes de desactivarlo). Al
            # desactivarlo sale de list_active(), así que el aviso se manda UNA
            # sola vez (sin flag "ya avisado"). Best-effort: un fallo de envío no
            # debe impedir la desactivación ni tumbar el job.
            if user.telegram_chat_id:
                try:
                    await notifier.send_message(
                        user,
                        message_builder.build_token_expired_message(web_relink_url),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send token-expired notice to user_id=%s", user.id
                    )
            user.deactivate()
            try:
                await user_repository.update(user)
            except Exception:
                logger.exception(
                    "Failed to deactivate user_id=%s after invalid Moodle token",
                    user.id,
                )
            logger.warning(
                "Deactivated user_id=%s moodle_user_id=%s: invalid Moodle token (%s)",
                user.id,
                user.moodle_user_id,
                exc,
            )
        except Exception as exc:
            failure_count += 1
            failures.append(
                ScanFailure(
                    moodle_user_id=user.moodle_user_id,
                    error=f"{type(exc).__name__}: {exc}"[:500],
                )
            )
            logger.exception(
                "Scheduled scan failed for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )

    finished_at = datetime.now(UTC)

    # Persistimos el resumen de la corrida (observabilidad). Un fallo al guardar
    # el historial no debe tumbar el job; solo lo logueamos.
    try:
        await get_scan_run_repository().save(
            ScanRun(
                job_name="scan",
                started_at=started_at,
                finished_at=finished_at,
                total_users=len(users),
                success_count=success_count,
                failure_count=failure_count,
                failures=failures,
            )
        )
    except Exception:
        logger.exception("Failed to persist scan run summary")

    logger.info(
        "Scheduled scan finished total=%s success=%s failure=%s",
        len(users),
        success_count,
        failure_count,
    )
