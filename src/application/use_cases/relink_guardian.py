import logging
from typing import Callable

from src.application.dto.guardian_dto import (
    RelinkGuardianInput,
    RelinkGuardianOutput,
)
from src.application.notification_subjects import SUBJECT_RELINK
from src.application.ports.notification_dispatcher import NotificationDispatcher
from src.domain.entities.moodle_site import get_site
from src.domain.exceptions.registration_errors import (
    RegistrationError,
    RelinkUserNotFoundError,
)
from src.domain.ports.moodle_connection_repository import MoodleConnectionRepository
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class RelinkGuardianUseCase:
    """Re-vincula el token de una CONEXIÓN existente (por campus) y la reactiva.

    Multi-campus: el token que muere es el de un campus concreto (aprende puede morir
    mientras educa sigue vivo), así que se re-vincula por `(site_key, moodle_user_id)`.
    Lo llama la web tras generar la llave del lado del usuario (el backend nunca ve
    credenciales).
    """

    def __init__(
        self,
        user_repository: UserRepository,
        connection_repository: MoodleConnectionRepository,
        moodle_gateway_factory: Callable[[str], MoodleGateway],
        dispatcher: NotificationDispatcher,
    ) -> None:
        self.user_repository = user_repository
        self.connection_repository = connection_repository
        self.moodle_gateway_factory = moodle_gateway_factory
        self.dispatcher = dispatcher

    async def execute(self, data: RelinkGuardianInput) -> RelinkGuardianOutput:
        # 1. Validar la llave nueva contra la URL del campus antes de tocar la DB.
        site = get_site(data.site_key)
        gateway = self.moodle_gateway_factory(site.base_url)
        if not await gateway.validate_token(data.moodle_token):
            raise RegistrationError("El token de Moodle no es válido.")

        # 2. La conexión debe existir (re-vincular ≠ registrar).
        connection = await self.connection_repository.get_by_site_and_moodle_user_id(
            data.site_key, data.moodle_user_id
        )
        if connection is None:
            raise RelinkUserNotFoundError(
                f"No hay una conexión registrada a {site.campus} con Moodle ID "
                f"{data.moodle_user_id}."
            )

        # 3. Actualizar token + reactivar la conexión.
        connection.relink(data.moodle_token)
        updated = await self.connection_repository.update(connection)

        # 4. Confirmación a la cuenta dueña por sus canales activos (best-effort).
        account = await self.user_repository.get_by_id(updated.account_id)
        if account is not None:
            try:
                await self.dispatcher.dispatch(
                    account,
                    lambda builder: builder.build_relink_success_message(),
                    subject=SUBJECT_RELINK,
                )
            except Exception:
                logger.exception(
                    "Failed to send relink confirmation to account_id=%s",
                    updated.account_id,
                )

        return RelinkGuardianOutput(
            user_id=updated.account_id,
            moodle_user_id=updated.moodle_user_id,
            is_active=updated.is_active,
            message="Vínculo reactivado correctamente.",
            site_key=updated.site_key,
        )
