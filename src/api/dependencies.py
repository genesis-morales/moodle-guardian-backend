from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.infrastructure.external.moodle.moodle_client import MoodleClient
from src.infrastructure.repositories.postgres_subscription_repository import (
    PostgresSubscriptionRepository,
)
from src.infrastructure.repositories.postgres_user_repository import (
    PostgresUserRepository,
)


def get_user_repository() -> PostgresUserRepository:
    return PostgresUserRepository()


def get_subscription_repository() -> PostgresSubscriptionRepository:
    return PostgresSubscriptionRepository()


def get_moodle_gateway() -> MoodleClient:
    return MoodleClient()


def get_register_guardian_use_case() -> RegisterGuardianUseCase:
    return RegisterGuardianUseCase(
        user_repository=get_user_repository(),
        subscription_repository=get_subscription_repository(),
        moodle_gateway=get_moodle_gateway(),
    )