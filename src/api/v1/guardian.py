import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from src.api.dependencies import (
    get_register_guardian_use_case,
    get_relink_guardian_use_case,
    get_run_guardian_scan_use_case,
)
from src.api.schemas.guardian import (
    RegisterGuardianRequest,
    RegisterGuardianResponse,
    RelinkGuardianRequest,
    RelinkGuardianResponse,
)
from src.application.dto.guardian_dto import RegisterGuardianInput, RelinkGuardianInput
from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.application.use_cases.relink_guardian import RelinkGuardianUseCase
from src.application.use_cases.run_guardian_scan import RunGuardianScanUseCase
from src.domain.exceptions.registration_errors import (
    RegistrationError,
    RelinkUserNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/guardian", tags=["Guardian"])


async def _capture_initial_snapshot(
    use_case: RunGuardianScanUseCase,
    moodle_user_id: int,
) -> None:
    """Captura el snapshot base del usuario recién registrado.

    Se ejecuta en segundo plano tras el registro para no bloquear la
    respuesta. Un fallo aquí no debe afectar al registro ya completado.
    """
    try:
        await use_case.execute(moodle_user_id)
        logger.info("Initial snapshot captured for moodle_user_id=%s", moodle_user_id)
    except Exception:
        logger.exception(
            "Initial guardian scan failed for moodle_user_id=%s", moodle_user_id
        )


@router.post(
    "/register",
    response_model=RegisterGuardianResponse,
    status_code=status.HTTP_200_OK,
)
async def register_guardian(
    payload: RegisterGuardianRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    use_case: RegisterGuardianUseCase = Depends(get_register_guardian_use_case),
    run_guardian_scan_use_case: RunGuardianScanUseCase = Depends(
        get_run_guardian_scan_use_case
    ),
) -> RegisterGuardianResponse:
    try:
        result = await use_case.execute(
            RegisterGuardianInput(
                moodle_user_id=payload.moodle_user_id,
                moodle_token=payload.moodle_token,
                telegram_chat_id=payload.telegram_chat_id,
            )
        )

        if result.message == "Usuario registrado correctamente.":
            response.status_code = status.HTTP_201_CREATED
            # Capturamos el snapshot base en segundo plano para que el usuario
            # tenga línea de referencia sin esperar al siguiente ciclo del scheduler.
            background_tasks.add_task(
                _capture_initial_snapshot,
                run_guardian_scan_use_case,
                result.moodle_user_id,
            )
        else:
            response.status_code = status.HTTP_200_OK

        return RegisterGuardianResponse(
            user_id=result.user_id,
            moodle_user_id=result.moodle_user_id,
            is_active=result.is_active,
            telegram_linked=result.telegram_linked,
            courses_count=result.courses_count,
            message=result.message,)

    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception:
        raise


@router.post(
    "/relink",
    response_model=RelinkGuardianResponse,
    status_code=status.HTTP_200_OK,
)
async def relink_guardian(
    payload: RelinkGuardianRequest,
    use_case: RelinkGuardianUseCase = Depends(get_relink_guardian_use_case),
) -> RelinkGuardianResponse:
    """Re-vincula un token nuevo y reactiva a un usuario existente cuyo token murió.

    Lo llama la web propia con la llave ya generada (el backend nunca ve credenciales).
    """
    try:
        result = await use_case.execute(
            RelinkGuardianInput(
                moodle_user_id=payload.moodle_user_id,
                moodle_token=payload.moodle_token,
            )
        )
        return RelinkGuardianResponse(
            user_id=result.user_id,
            moodle_user_id=result.moodle_user_id,
            is_active=result.is_active,
            message=result.message,
        )
    except RelinkUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc