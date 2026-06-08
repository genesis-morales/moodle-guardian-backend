from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_fetch_course_snapshot_use_case
from src.api.schemas.sync import ManualSyncRequest, ManualSyncResponse
from src.application.dto.sync_dto import ManualSyncInput
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.domain.exceptions.domain_errors import DomainError

router = APIRouter(prefix="/v1/sync", tags=["Sync"])


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