from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    get_telegram_message_builder,
    get_telegram_notifier,
    get_user_repository,
)
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.user import User
from src.domain.ports.notifier_gateway import NotifierGateway
from src.domain.ports.user_repository import UserRepository

router = APIRouter(prefix="/telegram", tags=["telegram"])


async def _get_user_with_telegram(
    moodle_user_id: int,
    user_repository: UserRepository,
) -> User:
    user = await user_repository.get_by_moodle_user_id(moodle_user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.telegram_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no linked telegram_chat_id",
        )

    return user


@router.post("/test/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def send_test_telegram_message(
    moodle_user_id: int,
    user_repository: UserRepository = Depends(get_user_repository),
    notifier: NotifierGateway = Depends(get_telegram_notifier),
    message_builder: NotificationMessageBuilder = Depends(
        get_telegram_message_builder
    ),
) -> dict:
    user = await _get_user_with_telegram(moodle_user_id, user_repository)

    message = message_builder.build_test_message()
    await notifier.send_message(user, message)

    return {
        "ok": True,
        "message": "Test Telegram message sent",
        "moodle_user_id": moodle_user_id,
        "chat_id": user.telegram_chat_id,
    }


@router.post("/welcome/{moodle_user_id}", status_code=status.HTTP_200_OK)
async def send_welcome_telegram_message(
    moodle_user_id: int,
    user_repository: UserRepository = Depends(get_user_repository),
    notifier: NotifierGateway = Depends(get_telegram_notifier),
    message_builder: NotificationMessageBuilder = Depends(
        get_telegram_message_builder
    ),
) -> dict:
    user = await _get_user_with_telegram(moodle_user_id, user_repository)

    message = message_builder.build_welcome_message()
    await notifier.send_message(user, message)

    return {
        "ok": True,
        "message": "Welcome Telegram message sent",
        "moodle_user_id": moodle_user_id,
        "chat_id": user.telegram_chat_id,
    }