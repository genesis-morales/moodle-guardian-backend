import logging

from src.application.dto.guardian_dto import (
    RelinkGuardianInput,
    RelinkGuardianOutput,
)
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.exceptions.registration_errors import (
    RegistrationError,
    RelinkUserNotFoundError,
)
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.notifier_gateway import NotifierGateway
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class RelinkGuardianUseCase:
    """Re-vincula el token de un usuario existente y lo reactiva.

    Lo llama la web propia tras generar la llave del lado del usuario (el backend
    nunca ve credenciales). Separado de RegisterGuardianUseCase: registrar rechaza
    duplicados; re-vincular exige que el usuario ya exista y lo reactiva.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        moodle_gateway: MoodleGateway,
        notifier: NotifierGateway,
        message_builder: NotificationMessageBuilder,
    ) -> None:
        self.user_repository = user_repository
        self.moodle_gateway = moodle_gateway
        self.notifier = notifier
        self.message_builder = message_builder

    async def execute(self, data: RelinkGuardianInput) -> RelinkGuardianOutput:
        # 1. Validar la llave nueva contra Moodle antes de tocar la DB.
        token_is_valid = await self.moodle_gateway.validate_token(data.moodle_token)
        if not token_is_valid:
            raise RegistrationError("El token de Moodle no es válido.")

        # 2. El usuario debe existir (re-vincular ≠ registrar).
        user = await self.user_repository.get_by_moodle_user_id(data.moodle_user_id)
        if user is None:
            raise RelinkUserNotFoundError(
                f"No hay un usuario registrado con Moodle ID {data.moodle_user_id}."
            )

        # 3. Actualizar token + reactivar.
        user.relink(data.moodle_token)
        updated_user = await self.user_repository.update(user)

        # 4. Confirmación por Telegram (best-effort: un fallo de envío no invalida
        #    el re-vínculo ya persistido).
        if updated_user.telegram_chat_id:
            try:
                message = self.message_builder.build_relink_success_message()
                await self.notifier.send_message(updated_user, message)
            except Exception:
                logger.exception(
                    "Failed to send relink confirmation to user_id=%s",
                    updated_user.id,
                )

        return RelinkGuardianOutput(
            user_id=updated_user.id,
            moodle_user_id=updated_user.moodle_user_id,
            is_active=updated_user.is_active,
            message="Vínculo reactivado correctamente.",
        )
