from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_register_guardian_use_case
from src.api.schemas.guardian import (
    RegisterGuardianRequest,
    RegisterGuardianResponse,
)
from src.application.dto.guardian_dto import RegisterGuardianInput
from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.domain.exceptions.registration_errors import RegistrationError

router = APIRouter(prefix="/v1/guardian", tags=["Guardian"])


@router.post(
    "/register",
    response_model=RegisterGuardianResponse,
    status_code=status.HTTP_200_OK,
)
async def register_guardian(
    payload: RegisterGuardianRequest,
    response: Response,
    use_case: RegisterGuardianUseCase = Depends(get_register_guardian_use_case),
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
        else:
            response.status_code = status.HTTP_200_OK

        return RegisterGuardianResponse.model_validate(result)

    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al registrar guardian.",
        ) from exc