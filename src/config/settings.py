from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Moodle Guardian API"
    app_version: str = "1.0.0"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/moodle_guardian"
    )

    moodle_base_url: str = Field(
        default="https://aprende.uned.ac.cr/webservice/rest/server.php"
    )
    moodle_site_info_function: str = "core_webservice_get_site_info"
    moodle_courses_function: str = "core_enrol_get_users_courses"
    moodle_calendar_events_function: str = "core_calendar_get_calendar_events"
    moodle_assignments_function: str = "mod_assign_get_assignments"

    telegram_bot_token: str | None = None
    telegram_api_base_url: str = "https://api.telegram.org"
    request_timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()