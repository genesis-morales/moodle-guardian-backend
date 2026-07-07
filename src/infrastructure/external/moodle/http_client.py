import httpx

from src.config.settings import get_settings
from src.domain.exceptions.domain_errors import (
    MoodleFeatureDisabledError,
    MoodleTokenError,
)

settings = get_settings()

# Errorcodes de Moodle que indican un token muerto (no se arregla reintentando):
# - invalidtoken:      "token not found" -> borrado/revocado. El cambio de
#                       contraseña del usuario BORRA el token (CVE-2016-7038),
#                       así que este también cubre ese caso.
# - invalidtimedtoken: "token expired" -> pasó su validuntil. Los tokens de
#                       moodle_mobile_app expiran por defecto a las 12 semanas,
#                       así que esta es la causa de muerte MÁS común.
_INVALID_TOKEN_ERRORCODES = {"invalidtoken", "invalidtimedtoken"}

# Errorcode de Moodle cuando la función pedida está apagada por config del sitio
# (p.ej. mensajería con `$CFG->messaging` desactivado). No se arregla
# reintentando ni revinculando: es decisión del admin del campus.
_FEATURE_DISABLED_ERRORCODES = {"disabled"}

class MoodleHttpClient:
    def __init__(self, base_url: str | None = None) -> None:
        # Multi-campus: la URL viene de la conexión (su MoodleSite). Si no se pasa,
        # cae al global `settings.moodle_base_url` (compat con el camino legacy).
        if base_url is not None:
            self.base_url = base_url
        else:
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
            errorcode = data.get("errorcode")
            if errorcode in _INVALID_TOKEN_ERRORCODES:
                raise MoodleTokenError(message)
            if errorcode in _FEATURE_DISABLED_ERRORCODES:
                raise MoodleFeatureDisabledError(message)
            raise ValueError(message)

        return data