from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.entities.moodle_site import is_valid_site
from src.domain.entities.subscription_plan import is_valid_plan


def _validate_site_key(value: str) -> str:
    if not is_valid_site(value):
        raise ValueError(f"site_key '{value}' desconocido")
    return value


def _validate_plan(value: str) -> str:
    if not is_valid_plan(value):
        raise ValueError(f"plan '{value}' desconocido")
    return value


def _validate_email(value: str) -> str:
    # Validación mínima (sin dependencia email-validator): identidad de cuenta.
    # El endurecimiento real (verificación por magic link) llega con la auth.
    v = value.strip()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 6:
        raise ValueError("email inválido")
    return v.lower()


class RegisterGuardianRequest(BaseModel):
    # Identidad de cuenta (independiente del canal). Requerido.
    email: str = Field(..., min_length=6)
    moodle_user_id: int = Field(..., gt=0)
    moodle_token: str = Field(..., min_length=1)
    # Campus/sitio Moodle al que pertenece la llave. Requerido, sin default.
    site_key: str = Field(..., min_length=1)
    # Tier elegido en la web. Opcional: si no llega, cae al free tier (Alerta).
    plan: str = Field(default="alerta", min_length=1)
    telegram_chat_id: str | None = None

    @field_validator("site_key")
    @classmethod
    def _site_key_known(cls, value: str) -> str:
        return _validate_site_key(value)

    @field_validator("plan")
    @classmethod
    def _plan_known(cls, value: str) -> str:
        return _validate_plan(value)

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return _validate_email(value)


class RegisterGuardianResponse(BaseModel):
    user_id: int
    moodle_user_id: int
    is_active: bool
    telegram_linked: bool
    courses_count: int
    message: str
    site_key: str | None = None
    plan: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RelinkGuardianRequest(BaseModel):
    site_key: str = Field(..., min_length=1)
    moodle_user_id: int = Field(..., gt=0)
    moodle_token: str = Field(..., min_length=1)

    @field_validator("site_key")
    @classmethod
    def _site_key_known(cls, value: str) -> str:
        return _validate_site_key(value)


class RelinkGuardianResponse(BaseModel):
    user_id: int
    moodle_user_id: int
    is_active: bool
    message: str
    site_key: str | None = None

    model_config = ConfigDict(from_attributes=True)
