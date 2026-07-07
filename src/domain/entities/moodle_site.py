"""Catálogo de sitios Moodle (institución + campus).

Reemplaza el `settings.moodle_base_url` global (seam #1 de saas-multitenancy): la URL
deja de ser única y pasa a derivarse del sitio al que pertenece cada `MoodleConnection`.

**Ningún sitio es default.** Todos son iguales en el catálogo; `site_key` viaja explícito
en el registro/relink (lo manda la web). No hay fallback encadenado a un campus: no todos
usan aprende, no todos usan educa.

Hoy es un catálogo en código (agregar universidad = agregar una fila acá). Está modelado
como dato para migrar a una tabla DB sin reescribir cuando entre una 3ª universidad.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MoodleSite:
    key: str            # identificador estable, viaja en site_key (p. ej. "aprende")
    institution: str    # "UNED"
    campus: str         # "Aprende U"
    label: str          # etiqueta corta para la notificación: "[Aprende]"
    base_url: str       # …/webservice/rest/server.php del sitio


MOODLE_SITES: dict[str, MoodleSite] = {
    "aprende": MoodleSite(
        key="aprende",
        institution="UNED",
        campus="Aprende U",
        label="Aprende",
        base_url="https://aprende.uned.ac.cr/webservice/rest/server.php",
    ),
    # ⚠️ URL tentativa: confirmar la real de educa antes de probar contra el sitio real.
    "educa": MoodleSite(
        key="educa",
        institution="UNED",
        campus="Educa U",
        label="Educa",
        base_url="https://educa.uned.ac.cr/webservice/rest/server.php",
    ),
}


class UnknownMoodleSiteError(ValueError):
    """El site_key no existe en el catálogo."""


def get_site(site_key: str) -> MoodleSite:
    """Devuelve el sitio del catálogo o falla claro si el key no existe.

    Falla explícito (en vez de caer a un default) para que un site_key inválido en el
    registro se rechace como error de validación, no se degrade silenciosamente a otro campus.
    """
    site = MOODLE_SITES.get(site_key)
    if site is None:
        raise UnknownMoodleSiteError(
            f"site_key '{site_key}' desconocido; válidos: {sorted(MOODLE_SITES)}"
        )
    return site


def is_valid_site(site_key: str) -> bool:
    return site_key in MOODLE_SITES
