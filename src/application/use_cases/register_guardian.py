from src.application.dto.guardian_dto import (
    RegisterGuardianInput,
    RegisterGuardianOutput,
)
from src.domain.entities.user import User
from src.domain.exceptions.registration_errors import RegistrationError
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.user_repository import UserRepository


class RegisterGuardianUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        moodle_gateway: MoodleGateway,
    ) -> None:
        self.user_repository = user_repository
        self.moodle_gateway = moodle_gateway

    async def execute(
            self,
            data: RegisterGuardianInput,
    ) -> RegisterGuardianOutput:
        # 1. Validar el token con Moodle
        token_is_valid = await self.moodle_gateway.validate_token(data.moodle_token)
        if not token_is_valid:
            raise RegistrationError("El token de Moodle no es válido.")

        # 2. Buscar si el usuario ya existe por Moodle ID
        existing_user = await self.user_repository.get_by_moodle_user_id(
            data.moodle_user_id
        )

        # 3. Si no existe, buscar si el Telegram Chat ID ya está tomado
        if existing_user is None and data.telegram_chat_id:
            existing_user = await self.user_repository.get_by_telegram_chat_id(
                data.telegram_chat_id
            )

        # Si ya existe, disparamos el error de inmediato
        if existing_user is not None:
            raise RegistrationError(
                f"El usuario con Moodle ID {data.moodle_user_id} o Telegram Chat ID ya se encuentra registrado."
            )

        # 4. Flujo de registro limpio (Solo llega aquí si es un usuario totalmente nuevo)
        user = User(
            id=None,
            moodle_user_id=data.moodle_user_id,
            moodle_token=data.moodle_token,
            telegram_chat_id=data.telegram_chat_id,
            is_active=True,
        )
        saved_user = await self.user_repository.save(user)
        message = "Usuario registrado correctamente."

        return RegisterGuardianOutput(
            user_id=saved_user.id,
            moodle_user_id=saved_user.moodle_user_id,
            is_active=saved_user.is_active,
            telegram_linked=saved_user.telegram_chat_id is not None,
            courses_count=0,
            message=message,
        )