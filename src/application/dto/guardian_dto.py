from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterGuardianInput:
    email: str
    moodle_user_id: int
    moodle_token: str
    site_key: str
    telegram_chat_id: Optional[str] = None


@dataclass
class RegisterGuardianOutput:
    user_id: int
    moodle_user_id: int
    is_active: bool
    telegram_linked: bool
    courses_count: int
    message: str
    site_key: Optional[str] = None


@dataclass
class RelinkGuardianInput:
    site_key: str
    moodle_user_id: int
    moodle_token: str


@dataclass
class RelinkGuardianOutput:
    user_id: int
    moodle_user_id: int
    is_active: bool
    message: str
    site_key: Optional[str] = None
