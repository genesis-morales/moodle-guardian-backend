from pydantic import BaseModel, Field, ConfigDict


class RegisterGuardianRequest(BaseModel):
    moodle_user_id: int = Field(..., gt=0)
    moodle_token: str = Field(..., min_length=1)
    telegram_chat_id: str | None = None


class RegisterGuardianResponse(BaseModel):
    user_id: int
    moodle_user_id: int
    is_active: bool
    telegram_linked: bool
    courses_count: int
    message: str

    model_config = ConfigDict(from_attributes=True)