import logging
from typing import Callable

from src.application.notification_subjects import SUBJECT_WELCOME
from src.application.ports.notification_dispatcher import NotificationDispatcher
from src.application.dto.guardian_dto import (
    RegisterGuardianInput,
    RegisterGuardianOutput,
)
from src.domain.entities.moodle_connection import MoodleConnection
from src.domain.entities.moodle_site import get_site
from src.domain.entities.subscription_plan import (
    CHANNEL_EMAIL,
    CHANNEL_TELEGRAM,
    plan_allows,
)
from src.domain.entities.user import User
from src.domain.exceptions.registration_errors import RegistrationError
from src.domain.ports.channel_preference_repository import (
    ChannelPreferenceRepository,
)
from src.domain.ports.moodle_connection_repository import MoodleConnectionRepository
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class RegisterGuardianUseCase:
    """Registra una cuenta (por email) y le vincula una conexión Moodle (por campus).

    - La identidad de la cuenta es el **email** (no el canal ni el moodle_user_id).
    - El token se valida contra la URL del **site_key** indicado (multi-campus).
    - Si el email ya tiene cuenta, se le **agrega** la conexión del nuevo campus (no se
      rechaza); si no existe, se crea la cuenta + su 1ª conexión.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        connection_repository: MoodleConnectionRepository,
        moodle_gateway_factory: Callable[[str], MoodleGateway],
        dispatcher: NotificationDispatcher,
        channel_preference_repository: ChannelPreferenceRepository,
    ) -> None:
        self.user_repository = user_repository
        self.connection_repository = connection_repository
        self.moodle_gateway_factory = moodle_gateway_factory
        self.dispatcher = dispatcher
        self.channel_preference_repository = channel_preference_repository

    async def execute(self, data: RegisterGuardianInput) -> RegisterGuardianOutput:
        # 1. Resolver el sitio y validar el token contra SU URL (no la global).
        site = get_site(data.site_key)
        gateway = self.moodle_gateway_factory(site.base_url)
        if not await gateway.validate_token(data.moodle_token):
            raise RegistrationError("El token de Moodle no es válido.")

        # 2. La conexión es única por (site_key, moodle_user_id): si ya existe, no se
        #    duplica (evita registrar dos veces el mismo campus/usuario).
        existing_connection = await self.connection_repository.get_by_site_and_moodle_user_id(
            data.site_key, data.moodle_user_id
        )
        if existing_connection is not None:
            raise RegistrationError(
                f"La conexión a {site.campus} (usuario {data.moodle_user_id}) ya está registrada."
            )

        # 3. Llave de cuenta = email.
        account = await self.user_repository.get_by_email(data.email)

        if account is None:
            # Cuenta nueva: la creamos (identidad email + canal opcional) y su 1ª conexión.
            # Las columnas legacy moodle_user_id/token del User se pueblan desde esta 1ª
            # conexión (compat con el scan legacy de fase 1).
            if data.telegram_chat_id:
                taken = await self.user_repository.get_by_telegram_chat_id(
                    data.telegram_chat_id
                )
                if taken is not None:
                    raise RegistrationError(
                        "Ese Telegram ya está vinculado a otra cuenta."
                    )
            account = await self.user_repository.save(
                User(
                    id=None,
                    moodle_user_id=data.moodle_user_id,
                    moodle_token=data.moodle_token,
                    email=data.email,
                    telegram_chat_id=data.telegram_chat_id,
                    plan=data.plan,
                    is_active=True,
                )
            )
            # Preferencias de canal (fuente de verdad de "por dónde notificar"):
            #  - telegram si el usuario pegó su chat_id.
            #  - email al correo de la cuenta, habilitado solo si el plan lo permite
            #    (si no, queda registrado pero apagado hasta que suba de tier).
            if data.telegram_chat_id:
                await self.channel_preference_repository.upsert(
                    account.id, CHANNEL_TELEGRAM, data.telegram_chat_id, is_enabled=True
                )
            await self.channel_preference_repository.upsert(
                account.id,
                CHANNEL_EMAIL,
                data.email,
                is_enabled=plan_allows(account.plan, CHANNEL_EMAIL),
            )

            message = "Usuario registrado correctamente."
            try:
                await self.dispatcher.dispatch(
                    account,
                    lambda builder: builder.build_welcome_message(),
                    subject=SUBJECT_WELCOME,
                )
            except Exception:
                logger.exception("Fallo al enviar el mensaje de bienvenida")
        else:
            # Cuenta existente: solo se le agrega el nuevo campus. El plan NO se cambia
            # acá: subir de tier es un flujo de upgrade con pago (feat 3), no un efecto
            # colateral de vincular otro campus. Se conserva el plan actual de la cuenta.
            message = f"Campus {site.campus} vinculado a tu cuenta."

        await self.connection_repository.save(
            MoodleConnection(
                id=None,
                account_id=account.id,
                site_key=data.site_key,
                moodle_user_id=data.moodle_user_id,
                moodle_token=data.moodle_token,
                is_active=True,
            )
        )

        return RegisterGuardianOutput(
            user_id=account.id,
            moodle_user_id=data.moodle_user_id,
            is_active=account.is_active,
            telegram_linked=account.telegram_chat_id is not None,
            courses_count=0,
            message=message,
            site_key=data.site_key,
            plan=account.plan,
        )
