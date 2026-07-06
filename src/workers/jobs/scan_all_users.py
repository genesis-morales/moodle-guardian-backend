import logging
from datetime import UTC, datetime

from src.api.dependencies import (
    get_moodle_connection_repository,
    get_run_guardian_scan_use_case,
    get_scan_run_repository,
    get_telegram_message_builder,
    get_telegram_notifier,
    get_user_repository,
)
from src.config.settings import get_settings
from src.domain.entities.moodle_site import get_site
from src.domain.entities.scan_run import ScanFailure, ScanRun
from src.domain.exceptions.domain_errors import MoodleTokenError

logger = logging.getLogger(__name__)


async def scan_all_users_job() -> None:
    """Scan programado, ahora POR CONEXIÓN (multi-campus).

    Itera las conexiones Moodle activas (no los usuarios): un usuario con 2 campus =
    2 iteraciones independientes. El token-recovery (umbral de fallos, desactivación,
    aviso de re-vínculo) es por conexión: el token de aprende puede morir sin afectar
    el de educa, y el aviso dice qué campus reactivar. La notificación de cambios sigue
    yendo al canal (Telegram) de la cuenta dueña.
    """
    logger.info("Starting scheduled scan for active connections")

    connection_repository = get_moodle_connection_repository()
    user_repository = get_user_repository()
    run_guardian_scan_use_case = get_run_guardian_scan_use_case()
    notifier = get_telegram_notifier()
    message_builder = get_telegram_message_builder()
    settings = get_settings()
    web_relink_url = settings.web_relink_url
    token_failure_threshold = settings.token_failure_threshold

    connections = await connection_repository.list_active()
    logger.info("Loaded active connections for scheduled scan count=%s", len(connections))

    started_at = datetime.now(UTC)
    success_count = 0
    failure_count = 0
    failures: list[ScanFailure] = []

    for connection in connections:
        try:
            logger.info(
                "Running scheduled scan connection_id=%s site=%s account_id=%s",
                connection.id,
                connection.site_key,
                connection.account_id,
            )
            await run_guardian_scan_use_case.execute_for_connection(connection)
            success_count += 1
            # Un scan sano resetea el contador de fallos de esa conexión.
            if connection.token_failure_count > 0:
                try:
                    await connection_repository.update_token_failure_count(
                        connection.id, 0
                    )
                except Exception:
                    logger.exception(
                        "Failed to reset token_failure_count for connection_id=%s",
                        connection.id,
                    )
        except MoodleTokenError as exc:
            # Token muerto según Moodle. Contamos fallos CONSECUTIVOS por conexión y
            # solo desactivamos+avisamos al alcanzar el umbral (un bache transitorio
            # no baja a nadie). Un scan exitoso resetea el contador.
            failure_count += 1
            connection.register_token_failure()

            if connection.token_failure_count < token_failure_threshold:
                failures.append(
                    ScanFailure(
                        moodle_user_id=connection.moodle_user_id,
                        error=(
                            f"MoodleTokenError [{connection.site_key}] (fallo "
                            f"{connection.token_failure_count}/{token_failure_threshold}, "
                            f"sin desactivar): {exc}"
                        )[:500],
                    )
                )
                try:
                    await connection_repository.update_token_failure_count(
                        connection.id, connection.token_failure_count
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist token_failure_count for connection_id=%s",
                        connection.id,
                    )
                logger.warning(
                    "Token failure %s/%s for connection_id=%s site=%s (no deactivation yet): %s",
                    connection.token_failure_count,
                    token_failure_threshold,
                    connection.id,
                    connection.site_key,
                    exc,
                )
                continue

            # Umbral alcanzado: avisar (con el campus) + desactivar la conexión.
            failures.append(
                ScanFailure(
                    moodle_user_id=connection.moodle_user_id,
                    error=(
                        f"MoodleTokenError [{connection.site_key}] (conexión desactivada "
                        f"tras {token_failure_threshold} fallos): {exc}"
                    )[:500],
                )
            )
            account = await user_repository.get_by_id(connection.account_id)
            if account is not None and account.telegram_chat_id:
                try:
                    site_label = get_site(connection.site_key).label
                    await notifier.send_message(
                        account,
                        message_builder.build_token_expired_message(
                            web_relink_url, site_label=site_label
                        ),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send token-expired notice for connection_id=%s",
                        connection.id,
                    )
            connection.deactivate()
            try:
                await connection_repository.update(connection)
            except Exception:
                logger.exception(
                    "Failed to deactivate connection_id=%s after invalid Moodle token",
                    connection.id,
                )
            logger.warning(
                "Deactivated connection_id=%s site=%s after %s consecutive token failures: %s",
                connection.id,
                connection.site_key,
                token_failure_threshold,
                exc,
            )
        except Exception as exc:
            failure_count += 1
            failures.append(
                ScanFailure(
                    moodle_user_id=connection.moodle_user_id,
                    error=f"{type(exc).__name__} [{connection.site_key}]: {exc}"[:500],
                )
            )
            logger.exception(
                "Scheduled scan failed for connection_id=%s site=%s",
                connection.id,
                connection.site_key,
            )

    finished_at = datetime.now(UTC)

    try:
        await get_scan_run_repository().save(
            ScanRun(
                job_name="scan",
                started_at=started_at,
                finished_at=finished_at,
                total_users=len(connections),
                success_count=success_count,
                failure_count=failure_count,
                failures=failures,
            )
        )
    except Exception:
        logger.exception("Failed to persist scan run summary")

    logger.info(
        "Scheduled scan finished total_connections=%s success=%s failure=%s",
        len(connections),
        success_count,
        failure_count,
    )
