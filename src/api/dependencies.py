from src.application.use_cases.run_guardian_scan import RunGuardianScanUseCase
from src.domain.services.diff_service import DiffService
from src.infrastructure.repositories.postgres_snapshot_repository import (
    PostgresSnapshotRepository,
)
from src.infrastructure.repositories.postgres_sent_reminder_repository import (
    PostgresSentReminderRepository,
)
from src.infrastructure.repositories.postgres_scan_run_repository import (
    PostgresScanRunRepository,
)
from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.application.use_cases.relink_guardian import RelinkGuardianUseCase
from src.infrastructure.repositories.postgres_user_repository import (
    PostgresUserRepository,
)
from src.infrastructure.repositories.postgres_moodle_connection_repository import (
    PostgresMoodleConnectionRepository,
)
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.config.settings import get_settings
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.notifier_gateway import NotifierGateway
from src.infrastructure.external.moodle.http_client import MoodleHttpClient
from src.infrastructure.external.moodle.moodle_client import MoodleClient
from src.infrastructure.external.moodle.fake_moodle_client import FakeMoodleClient
from src.infrastructure.external.telegram.fake_notifier import FakeNotifier
from src.application.use_cases.notify_user_changes import NotifyUserChangesUseCase
from src.application.use_cases.preview_notification import PreviewNotificationUseCase
from src.application.use_cases.build_weekly_digest import BuildWeeklyDigestUseCase
from src.application.use_cases.build_deadline_reminder import (
    BuildDeadlineReminderUseCase,
)
from src.application.use_cases.send_weekly_digest import SendWeeklyDigestUseCase
from src.application.use_cases.send_deadline_reminders import (
    SendDeadlineRemindersUseCase,
)
from src.infrastructure.external.telegram.telegram_bot import TelegramBotNotifier
from src.infrastructure.external.telegram.message_builder import (
    TelegramMessageBuilder,
)

def get_user_repository() -> PostgresUserRepository:
    return PostgresUserRepository()


def get_moodle_connection_repository() -> PostgresMoodleConnectionRepository:
    return PostgresMoodleConnectionRepository()


def get_snapshot_repository() -> PostgresSnapshotRepository:
    return PostgresSnapshotRepository()


def get_sent_reminder_repository() -> PostgresSentReminderRepository:
    return PostgresSentReminderRepository()


def get_scan_run_repository() -> PostgresScanRunRepository:
    return PostgresScanRunRepository()


def get_moodle_http_client() -> MoodleHttpClient:
    return MoodleHttpClient()


# --- Selección real vs fake según el perfil de entorno (ver settings) ---
# El composition root es el ÚNICO lugar que decide real/fake. Helpers puros
# (reciben el entorno) para poder testear la selección sin tocar env vars.
def _moodle_gateway_for(environment: str, base_url: str | None = None) -> MoodleGateway:
    if environment == "local":
        return FakeMoodleClient()
    return MoodleClient(http_client=MoodleHttpClient(base_url))


def get_moodle_gateway_for(base_url: str) -> MoodleGateway:
    """Gateway ligado a la URL de un sitio Moodle concreto (multi-campus).

    El scan/registro por conexión resuelve `base_url` desde el `MoodleSite` de la
    conexión y pide aquí un cliente apuntando a ese campus. En local se ignora la URL
    (el fake no pega a la red)."""
    return _moodle_gateway_for(get_settings().environment, base_url)


def _notifier_for(environment: str) -> NotifierGateway:
    if environment == "prod":
        return TelegramBotNotifier()
    return FakeNotifier()


def get_moodle_gateway() -> MoodleGateway:
    return _moodle_gateway_for(get_settings().environment)


def get_telegram_notifier() -> NotifierGateway:
    return _notifier_for(get_settings().environment)


def get_telegram_message_builder() -> TelegramMessageBuilder:
    return TelegramMessageBuilder()


def get_diff_service() -> DiffService:
    return DiffService()


def get_register_guardian_use_case() -> RegisterGuardianUseCase:
    return RegisterGuardianUseCase(
        user_repository=get_user_repository(),
        connection_repository=get_moodle_connection_repository(),
        moodle_gateway_factory=get_moodle_gateway_for,
        notifier=get_telegram_notifier(),
        message_builder=get_telegram_message_builder(),
    )


def get_relink_guardian_use_case() -> RelinkGuardianUseCase:
    return RelinkGuardianUseCase(
        user_repository=get_user_repository(),
        connection_repository=get_moodle_connection_repository(),
        moodle_gateway_factory=get_moodle_gateway_for,
        notifier=get_telegram_notifier(),
        message_builder=get_telegram_message_builder(),
    )


def get_fetch_course_snapshot_use_case() -> FetchCourseSnapshotUseCase:
    return FetchCourseSnapshotUseCase(
        user_repository=get_user_repository(),
        moodle_gateway=get_moodle_gateway(),
    )


def get_notify_user_changes_use_case() -> NotifyUserChangesUseCase:
    return NotifyUserChangesUseCase(
        notifier=get_telegram_notifier(),
        message_builder=get_telegram_message_builder(),
    )


def get_run_guardian_scan_use_case() -> RunGuardianScanUseCase:
    return RunGuardianScanUseCase(
        user_repository=get_user_repository(),
        snapshot_repository=get_snapshot_repository(),
        fetch_course_snapshot_use_case=get_fetch_course_snapshot_use_case(),
        diff_service=get_diff_service(),
        notify_user_changes_use_case=get_notify_user_changes_use_case(),
    )


def get_preview_notification_use_case() -> PreviewNotificationUseCase:
    return PreviewNotificationUseCase(
        user_repository=get_user_repository(),
        snapshot_repository=get_snapshot_repository(),
        fetch_course_snapshot_use_case=get_fetch_course_snapshot_use_case(),
        diff_service=get_diff_service(),
        message_builder=get_telegram_message_builder(),
        notifier=get_telegram_notifier(),
    )


def get_build_weekly_digest_use_case() -> BuildWeeklyDigestUseCase:
    return BuildWeeklyDigestUseCase(
        fetch_course_snapshot_use_case=get_fetch_course_snapshot_use_case(),
        message_builder=get_telegram_message_builder(),
    )


def get_build_deadline_reminder_use_case() -> BuildDeadlineReminderUseCase:
    return BuildDeadlineReminderUseCase(
        fetch_course_snapshot_use_case=get_fetch_course_snapshot_use_case(),
        message_builder=get_telegram_message_builder(),
        user_repository=get_user_repository(),
        sent_reminder_repository=get_sent_reminder_repository(),
    )


def get_send_weekly_digest_use_case() -> SendWeeklyDigestUseCase:
    return SendWeeklyDigestUseCase(
        user_repository=get_user_repository(),
        build_weekly_digest_use_case=get_build_weekly_digest_use_case(),
        notifier=get_telegram_notifier(),
        sent_reminder_repository=get_sent_reminder_repository(),
    )


def get_send_deadline_reminders_use_case() -> SendDeadlineRemindersUseCase:
    return SendDeadlineRemindersUseCase(
        user_repository=get_user_repository(),
        build_deadline_reminder_use_case=get_build_deadline_reminder_use_case(),
        notifier=get_telegram_notifier(),
        sent_reminder_repository=get_sent_reminder_repository(),
    )