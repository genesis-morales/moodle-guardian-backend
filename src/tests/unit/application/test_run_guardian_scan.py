import pytest
from unittest.mock import AsyncMock, Mock

from src.application.dto.sync_dto import (
    AssignmentItemOutput,
    CalendarEventItemOutput,
    ManualSyncOutput,
)
from src.application.use_cases.run_guardian_scan import RunGuardianScanUseCase
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User

pytestmark = pytest.mark.anyio

def build_user() -> User:
    return User(
        id=1,
        moodle_user_id=3095,
        moodle_token="token-123",
        telegram_chat_id="chat-123",
    )


def build_sync_output() -> ManualSyncOutput:
    return ManualSyncOutput(
        moodle_user_id=3095,
        courses_count=1,
        assignments_count=1,
        events_count=1,
        assignments=[
            AssignmentItemOutput(
                moodle_assignment_id=10,
                moodle_course_id=20,
                name="Foro 1",
                due_date=1718044800,
                allow_submissions_from=1717958400,
                cutoff_date=1718131200,
            )
        ],
        events=[
            CalendarEventItemOutput(
                moodle_event_id=30,
                course_id=20,
                name="Apertura foro",
                event_type="open",
                due_date=1718044800,
                url="https://moodle.test/event/30",
            )
        ],
    )


@pytest.mark.anyio
async def test_execute_raises_when_user_not_found():
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch_course_snapshot_use_case = Mock()
    diff_service = Mock()
    notify_user_changes_use_case = Mock()

    user_repository.get_by_moodle_user_id = AsyncMock(return_value=None)

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch_course_snapshot_use_case,
        diff_service=diff_service,
        notify_user_changes_use_case=notify_user_changes_use_case,
    )

    with pytest.raises(ValueError, match="User not found"):
        await use_case.execute(3095)


@pytest.mark.anyio
async def test_execute_first_run_uses_empty_diff_and_skips_compare():
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch_course_snapshot_use_case = Mock()
    diff_service = Mock()
    notify_user_changes_use_case = Mock()

    user = build_user()
    sync_output = build_sync_output()

    user_repository.get_by_moodle_user_id = AsyncMock(return_value=user)
    snapshot_repository.get_latest_by_user_id = AsyncMock(return_value=None)
    snapshot_repository.save = AsyncMock()
    fetch_course_snapshot_use_case.execute = AsyncMock(return_value=sync_output)
    notify_user_changes_use_case.execute = AsyncMock(return_value=False)

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch_course_snapshot_use_case,
        diff_service=diff_service,
        notify_user_changes_use_case=notify_user_changes_use_case,
    )

    result = await use_case.execute(3095)

    assert result.user == user
    assert result.previous_snapshot is None
    assert isinstance(result.diff, DiffResult)
    assert result.diff.has_changes is False
    assert result.notification_sent is False

    snapshot_repository.get_latest_by_user_id.assert_awaited_once_with(user.id)
    fetch_course_snapshot_use_case.execute.assert_awaited_once()
    snapshot_repository.save.assert_awaited_once()
    notify_user_changes_use_case.execute.assert_awaited_once_with(
        user=user,
        diff=result.diff,
    )
    diff_service.compare.assert_not_called()


@pytest.mark.anyio
async def test_execute_with_previous_snapshot_calls_compare():
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch_course_snapshot_use_case = Mock()
    diff_service = Mock()
    notify_user_changes_use_case = Mock()

    user = build_user()
    sync_output = build_sync_output()
    previous_snapshot = object()
    expected_diff = DiffResult()

    user_repository.get_by_moodle_user_id = AsyncMock(return_value=user)
    snapshot_repository.get_latest_by_user_id = AsyncMock(return_value=previous_snapshot)
    snapshot_repository.save = AsyncMock()
    fetch_course_snapshot_use_case.execute = AsyncMock(return_value=sync_output)
    diff_service.compare = Mock(return_value=expected_diff)
    notify_user_changes_use_case.execute = AsyncMock(return_value=False)

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch_course_snapshot_use_case,
        diff_service=diff_service,
        notify_user_changes_use_case=notify_user_changes_use_case,
    )

    result = await use_case.execute(3095)

    assert result.previous_snapshot is previous_snapshot
    assert result.diff is expected_diff
    diff_service.compare.assert_called_once()
    snapshot_repository.save.assert_awaited_once()
    notify_user_changes_use_case.execute.assert_awaited_once_with(
        user=user,
        diff=expected_diff,
    )


@pytest.mark.anyio
async def test_execute_returns_notification_sent_from_notifier_use_case():
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch_course_snapshot_use_case = Mock()
    diff_service = Mock()
    notify_user_changes_use_case = Mock()

    user = build_user()
    sync_output = build_sync_output()
    previous_snapshot = object()
    expected_diff = DiffResult(
        new_assignments=[],
        updated_assignments=[],
        removed_assignments=[],
        new_events=[],
        updated_events=[],
        removed_events=[],
    )

    user_repository.get_by_moodle_user_id = AsyncMock(return_value=user)
    snapshot_repository.get_latest_by_user_id = AsyncMock(return_value=previous_snapshot)
    snapshot_repository.save = AsyncMock()
    fetch_course_snapshot_use_case.execute = AsyncMock(return_value=sync_output)
    diff_service.compare = Mock(return_value=expected_diff)
    notify_user_changes_use_case.execute = AsyncMock(return_value=True)

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch_course_snapshot_use_case,
        diff_service=diff_service,
        notify_user_changes_use_case=notify_user_changes_use_case,
    )

    result = await use_case.execute(3095)

    assert result.notification_sent is True


@pytest.mark.anyio
async def test_execute_does_not_save_snapshot_when_notification_fails():
    """Invariante: si el envío de la notificación falla, el snapshot NO debe
    guardarse, para que el cambio se reintente en el próximo scan en vez de
    quedar consumido en el baseline (aviso perdido)."""
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch_course_snapshot_use_case = Mock()
    diff_service = Mock()
    notify_user_changes_use_case = Mock()

    user = build_user()
    sync_output = build_sync_output()
    previous_snapshot = object()
    expected_diff = DiffResult(new_events=[object()])

    user_repository.get_by_moodle_user_id = AsyncMock(return_value=user)
    snapshot_repository.get_latest_by_user_id = AsyncMock(return_value=previous_snapshot)
    snapshot_repository.save = AsyncMock()
    fetch_course_snapshot_use_case.execute = AsyncMock(return_value=sync_output)
    diff_service.compare = Mock(return_value=expected_diff)
    notify_user_changes_use_case.execute = AsyncMock(
        side_effect=RuntimeError("telegram down")
    )

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch_course_snapshot_use_case,
        diff_service=diff_service,
        notify_user_changes_use_case=notify_user_changes_use_case,
    )

    with pytest.raises(RuntimeError, match="telegram down"):
        await use_case.execute(3095)

    snapshot_repository.save.assert_not_awaited()

# --- scan por conexión (multi-campus) ---

def _connection(conn_id=11, account_id=1, site_key="aprende", moodle_user_id=42):
    from src.domain.entities.moodle_connection import MoodleConnection
    return MoodleConnection(
        id=conn_id, account_id=account_id, site_key=site_key,
        moodle_user_id=moodle_user_id, moodle_token="tok",
    )


@pytest.mark.anyio
async def test_execute_for_connection_first_run_saves_baseline_by_connection():
    from src.domain.entities.moodle_connection import MoodleConnection

    user_repository = Mock()
    snapshot_repository = Mock()
    fetch = Mock()
    diff_service = Mock()
    notify = Mock()
    conn_repo = Mock()

    account = build_user()
    connection = _connection()

    user_repository.get_by_id = AsyncMock(return_value=account)
    snapshot_repository.get_latest_by_connection_id = AsyncMock(return_value=None)
    snapshot_repository.save = AsyncMock()
    fetch.execute_for_connection = AsyncMock(return_value=build_sync_output())
    notify.execute = AsyncMock(return_value=False)
    # Mono-campus: 1 sola conexión -> sin etiqueta.
    conn_repo.list_by_account_id = AsyncMock(return_value=[connection])

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch,
        diff_service=diff_service,
        notify_user_changes_use_case=notify,
        connection_repository=conn_repo,
    )

    result = await use_case.execute_for_connection(connection)

    assert result.diff.has_changes is False
    diff_service.compare.assert_not_called()
    # Snapshot guardado con connection_id de la conexión.
    saved = snapshot_repository.save.await_args.args[0]
    assert saved.connection_id == connection.id
    assert saved.user_id == account.id
    # Mono-campus: notifica sin etiqueta de campus.
    notify.execute.assert_awaited_once_with(user=account, diff=result.diff, site_label=None)


@pytest.mark.anyio
async def test_execute_for_connection_tags_campus_when_multiple_connections():
    user_repository = Mock()
    snapshot_repository = Mock()
    fetch = Mock()
    diff_service = Mock()
    notify = Mock()
    conn_repo = Mock()

    account = build_user()
    connection = _connection(site_key="educa")

    user_repository.get_by_id = AsyncMock(return_value=account)
    snapshot_repository.get_latest_by_connection_id = AsyncMock(return_value=None)
    snapshot_repository.save = AsyncMock()
    fetch.execute_for_connection = AsyncMock(return_value=build_sync_output())
    notify.execute = AsyncMock(return_value=False)
    # 2 conexiones activas -> se etiqueta el campus.
    conn_repo.list_by_account_id = AsyncMock(
        return_value=[connection, _connection(conn_id=12, site_key="aprende")]
    )

    use_case = RunGuardianScanUseCase(
        user_repository=user_repository,
        snapshot_repository=snapshot_repository,
        fetch_course_snapshot_use_case=fetch,
        diff_service=diff_service,
        notify_user_changes_use_case=notify,
        connection_repository=conn_repo,
    )

    await use_case.execute_for_connection(connection)

    # 2 campus activos -> la notificación se etiqueta con el campus escaneado.
    assert notify.execute.await_args.kwargs["site_label"] == "Educa"
    assert notify.execute.await_args.kwargs["user"] is account
