from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterGuardianInput:
    moodle_user_id: int
    moodle_token: str
    telegram_chat_id: Optional[str] = None


@dataclass
class RegisterGuardianOutput:
    user_id: int
    moodle_user_id: int
    is_active: bool
    telegram_linked: bool
    courses_count: int
    message: str


@dataclass
class RelinkGuardianInput:
    moodle_user_id: int
    moodle_token: str


@dataclass
class RelinkGuardianOutput:
    user_id: int
    moodle_user_id: int
    is_active: bool
    message: str