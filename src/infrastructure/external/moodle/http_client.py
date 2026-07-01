import httpx

from src.config.settings import get_settings
from src.domain.exceptions.domain_errors import MoodleTokenError

settings = get_settings()

# Errorcodes de Moodle que indican un token inválido/expirado (no reintentar).
_INVALID_TOKEN_ERRORCODES = {"invalidtoken"}

class MoodleHttpClient:
    def __init__(self) -> None:
        self.base_url = settings.moodle_base_url.rstrip("/") + "/webservice/rest/server.php"

    async def call(
        self,
        token: str,
        wsfunction: str,
        params: dict | None = None,
    ) -> dict:
        query = {
            "wstoken": token,
            "moodlewsrestformat": "json",
            "wsfunction": wsfunction,
        }

        if params:
            query.update(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=query)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and data.get("exception"):
            message = data.get("message", "Error en Moodle web service.")
            if data.get("errorcode") in _INVALID_TOKEN_ERRORCODES:
                raise MoodleTokenError(message)
            raise ValueError(message)

        return data