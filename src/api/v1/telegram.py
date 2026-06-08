from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_telegram_notifier, get_user_repository
from src.domain.ports.notifier_gateway import NotifierGateway
from src.domain.ports.user_repository import UserRepository
from src.infrastructure.external.telegram.message_builder import build_test_message

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/test/{user_id}", status_code=status.HTTP_200_OK)
async def send_test_telegram_message(
    user_id: int,
    user_repository: UserRepository = Depends(get_user_repository),
    notifier: NotifierGateway = Depends(get_telegram_notifier),
) -> dict:
    user = await user_repository.get_by_id(user_id)

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

    await notifier.send_message(user, build_test_message())

    return {
        "ok": True,
        "message": "Test Telegram message sent",
        "user_id": user_id,
        "chat_id": user.telegram_chat_id,
    }