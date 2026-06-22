from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    get_build_deadline_reminder_use_case,
    get_build_weekly_digest_use_case,
    get_fetch_course_snapshot_use_case,
    get_preview_notification_use_case,
    get_run_guardian_scan_use_case,
    get_sent_reminder_repository,
    get_telegram_notifier,
    get_user_repository,
)
from src.domain.ports.sent_reminder_repository import NOTIFICATION_REMINDER
from src.api.schemas.sync import ManualSyncRequest, ManualSyncResponse
from src.application.dto.sync_dto import ManualSyncInput
from src.application.use_cases.build_deadline_reminder import (
    BuildDeadlineReminderUseCase,
)
from src.application.use_cases.build_weekly_digest import BuildWeeklyDigestUseCase
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.preview_notification import PreviewNotificationUseCase
from src.application.use_cases.run_guardian_scan import RunGuardianScanUseCase
from src.domain.exceptions.domain_errors import DomainError

router = APIRouter(prefix="/v1/sync", tags=["sync"])


@router.post(
    "/manual",
    response_model=ManualSyncResponse,
    status_code=status.HTTP_200_OK,
)
async def manual_sync(
    payload: ManualSyncRequest,
    use_case: FetchCourseSnapshotUseCase = Depends(get_fetch_course_snapshot_use_case),
) -> ManualSyncResponse:
    try:
        result = await use_case.execute(
            ManualSyncInput(moodle_user_id=payload.moodle_user_id)
        )

        return ManualSyncResponse(
            moodle_user_id=result.moodle_user_id,
            courses_count=result.courses_count,
            assignments_count=result.assignments_count,
            events_count=result.events_count,
            assignments=[
                {
                    "moodle_assignment_id": item.moodle_assignment_id,
                    "moodle_course_id": item.moodle_course_id,
                    "name": item.name,
                    "due_date": item.due_date,
                    "allow_submissions_from": item.allow_submissions_from,
                    "cutoff_date": item.cutoff_date,
                }
                for item in result.assignments
            ],
            events=[
                {
                    "moodle_event_id": item.moodle_event_id,
                    "course_id": item.course_id,
                    "name": item.name,
                    "event_type": item.event_type,
                    "due_date": item.due_date,
                    "url": item.url,
                }
                for item in result.events
            ],
        )

    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/preview/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def preview_notification(
    moodle_user_id: int,
    mode: str = "diff",
    send: bool = False,
    use_case: PreviewNotificationUseCase = Depends(get_preview_notification_use_case),
) -> dict:
    """Debug read-only: muestra el mensaje que se notificaría, sin guardar snapshot.

    - ?mode=diff (default): lo que SÍ dispararía (diff vs último snapshot).
    - ?mode=all: todo lo actual como nuevo (para revisar formato).
    - ?send=true: además lo envía al Telegram del usuario.
    """
    try:
        result = await use_case.execute(moodle_user_id, mode=mode, send=send)

        return {
            "ok": True,
            "moodle_user_id": result.moodle_user_id,
            "mode": result.mode,
            "has_changes": result.has_changes,
            "sent": result.sent,
            "events_new": result.events_new,
            "events_updated": result.events_updated,
            "events_removed": result.events_removed,
            "assignments_new": result.assignments_new,
            "assignments_updated": result.assignments_updated,
            "assignments_removed": result.assignments_removed,
            "message": result.message,
        }

    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        # mode inválido -> 400; usuario no encontrado -> 404.
        if "mode inválido" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/digest/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def preview_weekly_digest(
    moodle_user_id: int,
    send: bool = False,
    use_case: BuildWeeklyDigestUseCase = Depends(get_build_weekly_digest_use_case),
) -> dict:
    """Debug: muestra el digest semanal (todo lo pendiente futuro). ?send=true lo envía."""
    message = await use_case.execute(moodle_user_id)

    sent = False
    if send:
        user = await get_user_repository().get_by_moodle_user_id(moodle_user_id)
        if user and user.telegram_chat_id:
            await get_telegram_notifier().send_message(user, message)
            sent = True

    return {"ok": True, "moodle_user_id": moodle_user_id, "sent": sent, "message": message}


@router.post("/reminders/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def preview_deadline_reminder(
    moodle_user_id: int,
    send: bool = False,
    days: int | None = None,
    use_case: BuildDeadlineReminderUseCase = Depends(
        get_build_deadline_reminder_use_case
    ),
) -> dict:
    """Debug READ-ONLY: muestra el recordatorio de entregas próximas (o null si
    no hay nada nuevo). NO registra nada en el historial — eso solo lo hace el
    job real. ?days=N prueba otro horizonte; ?send=true lo envía (y registra)."""
    preview = await use_case.execute(moodle_user_id, days=days)
    message = preview.message

    sent = False
    if send and message is not None:
        user = await get_user_repository().get_by_moodle_user_id(moodle_user_id)
        if user and user.telegram_chat_id:
            await get_telegram_notifier().send_message(user, message)
            for item in preview.items:
                await get_sent_reminder_repository().record(
                    user_id=user.id,
                    notification_type=NOTIFICATION_REMINDER,
                    deliverable_key=item.key,
                    deadline_snapshot=item.deadline,
                )
            sent = True

    return {"ok": True, "moodle_user_id": moodle_user_id, "sent": sent, "message": message}


@router.post("/run/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def run_guardian_scan(
    moodle_user_id: int,
    use_case: RunGuardianScanUseCase = Depends(get_run_guardian_scan_use_case),
) -> dict:
    try:
        result = await use_case.execute(moodle_user_id)

        return {
            "ok": True,
            "moodle_user_id": moodle_user_id,
            "has_changes": result.diff.has_changes,
            "notification_sent": result.notification_sent,
            "assignments_new": len(result.diff.new_assignments),
            "assignments_updated": len(result.diff.updated_assignments),
            "assignments_removed": len(result.diff.removed_assignments),
            "events_new": len(result.diff.new_events),
            "events_updated": len(result.diff.updated_events),
            "events_removed": len(result.diff.removed_events),
            "captured_at": result.current_snapshot.captured_at.isoformat(),
        }

    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc