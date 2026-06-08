from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.infrastructure.external.moodle.moodle_client import MoodleClient
from src.infrastructure.external.moodle.http_client import MoodleHttpClient
from src.infrastructure.external.telegram.telegram_bot import TelegramBotNotifier
from src.infrastructure.repositories.postgres_subscription_repository import (PostgresSubscriptionRepository,)
from src.infrastructure.repositories.postgres_user_repository import (PostgresUserRepository,)
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.infrastructure.external.moodle.http_client import MoodleHttpClient
from src.infrastructure.external.moodle.moodle_client import MoodleClient


def get_user_repository() -> PostgresUserRepository:
    return PostgresUserRepository()


def get_subscription_repository() -> PostgresSubscriptionRepository:
    return PostgresSubscriptionRepository()


def get_moodle_http_client() -> MoodleHttpClient:
    return MoodleHttpClient()


def get_moodle_gateway() -> MoodleClient:
    return MoodleClient(http_client=get_moodle_http_client())


def get_telegram_notifier() -> TelegramBotNotifier:
    return TelegramBotNotifier()


def get_register_guardian_use_case() -> RegisterGuardianUseCase:
    return RegisterGuardianUseCase(
        user_repository=get_user_repository(),
        subscription_repository=get_subscription_repository(),
        moodle_gateway=get_moodle_gateway(),
    )


def get_fetch_course_snapshot_use_case() -> FetchCourseSnapshotUseCase:
    return FetchCourseSnapshotUseCase(
        user_repository=get_user_repository(),
        subscription_repository=get_subscription_repository(),
        moodle_gateway=get_moodle_gateway(),
    )