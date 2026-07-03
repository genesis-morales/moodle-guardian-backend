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
    settings = get_settings()
    web_relink_url = settings.web_relink_url
    token_failure_threshold = settings.token_failure_threshold

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
            # Un scan sano resetea el contador de fallos (solo escribimos si hay
            # algo que limpiar, para no pegarle a la DB en cada corrida normal).
            if user.token_failure_count > 0:
                try:
                    await user_repository.update_token_failure_count(
                        user.moodle_user_id, 0
                    )
                except Exception:
                    logger.exception(
                        "Failed to reset token_failure_count for user_id=%s", user.id
                    )
        except MoodleTokenError as exc:
            # Token inválido/expirado según Moodle. Puede ser real (revocado/
            # expirado) o un bache transitorio de la UNED. NO desactivamos al
            # primer fallo: contamos fallos CONSECUTIVOS y solo desactivamos al
            # alcanzar el umbral, para que un bache no baje a nadie. Un scan
            # exitoso resetea el contador. WARNING (sin traceback) para no generar
            # evento Sentry por algo esperado.
            failure_count += 1
            user.register_token_failure()

            if user.token_failure_count < token_failure_threshold:
                # Dentro del margen: registramos el fallo y seguimos, sin avisar
                # ni desactivar (puede recuperarse en la próxima corrida).
                failures.append(
                    ScanFailure(
                        moodle_user_id=user.moodle_user_id,
                        error=(
                            f"MoodleTokenError (fallo {user.token_failure_count}/"
                            f"{token_failure_threshold}, sin desactivar): {exc}"
                        )[:500],
                    )
                )
                try:
                    await user_repository.update_token_failure_count(
                        user.moodle_user_id, user.token_failure_count
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist token_failure_count for user_id=%s",
                        user.id,
                    )
                logger.warning(
                    "Token failure %s/%s for user_id=%s moodle_user_id=%s "
                    "(no deactivation yet): %s",
                    user.token_failure_count,
                    token_failure_threshold,
                    user.id,
                    user.moodle_user_id,
                    exc,
                )
                continue

            # Alcanzó el umbral: ahora sí avisamos + desactivamos. Al desactivar
            # sale de list_active(), así que el aviso se manda UNA sola vez.
            failures.append(
                ScanFailure(
                    moodle_user_id=user.moodle_user_id,
                    error=(
                        f"MoodleTokenError (usuario desactivado tras "
                        f"{token_failure_threshold} fallos): {exc}"
                    )[:500],
                )
            )
            # Best-effort: un fallo de envío no debe impedir la desactivación ni
            # tumbar el job.
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
                "Deactivated user_id=%s moodle_user_id=%s after %s consecutive "
                "token failures: %s",
                user.id,
                user.moodle_user_id,
                token_failure_threshold,
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
