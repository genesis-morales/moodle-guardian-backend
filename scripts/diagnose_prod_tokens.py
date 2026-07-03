"""Diagnóstico read-only de los tokens en una BD (pensado para prod).

Responde: ¿el token en la BD está bien cifrado y sigue vivo en Moodle, o murió?
NO escribe nada y NUNCA imprime el token en claro (solo largo/forma + veredicto).

Uso (PowerShell / bash):
    PROD_DATABASE_URL="postgresql://neondb_owner:...@.../neondb" \
    TOKEN_ENCRYPTION_KEY="<tu key>" \
    python scripts/diagnose_prod_tokens.py

Si no pasás PROD_DATABASE_URL usa DATABASE_URL del .env (branch dev, vacío).
"""

import asyncio
import os
import re

import sys

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Permite `python scripts/diagnose_prod_tokens.py` desde cualquier lado: mete la
# raíz del proyecto en el path para que `import src...` funcione.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings  # noqa: E402
from src.infrastructure.security.token_cipher import TokenCipher

# Forma de un token de webservice de Moodle: 32 hex.
_MOODLE_TOKEN_RE = re.compile(r"^[a-f0-9]{32}$")


def _normalize_async(url: str) -> str:
    """Deja la URL lista para asyncpg: driver correcto y sin query params que
    asyncpg no entiende (sslmode/channel_binding, típicos de la URL de Neon).
    El SSL se activa aparte, con connect_args, en create_async_engine."""
    # Cortamos el query string entero (?sslmode=require&channel_binding=...):
    # asyncpg no acepta esos params y el SSL lo forzamos nosotros.
    url = url.split("?", 1)[0]
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


async def _moodle_verdict(base_url: str, token: str) -> str:
    """Llama a get_site_info igual que el scan y clasifica la respuesta."""
    url = base_url.rstrip("/") + "/webservice/rest/server.php"
    params = {
        "wstoken": token,
        "moodlewsrestformat": "json",
        "wsfunction": "core_webservice_get_site_info",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - queremos ver cualquier fallo
        return f"ERROR de red/HTTP: {type(exc).__name__}: {exc}"

    if isinstance(data, dict) and data.get("exception"):
        return f"MUERTO ({data.get('errorcode')}): {data.get('message')}"
    if isinstance(data, dict) and "userid" in data:
        return f"VIVO (userid={data['userid']}, sitio={data.get('sitename', '?')})"
    return f"RESPUESTA INESPERADA: {str(data)[:120]}"


async def main() -> None:
    settings = get_settings()
    db_url = os.environ.get("PROD_DATABASE_URL") or settings.database_url
    db_url = _normalize_async(db_url)

    keys = settings.token_encryption_keys
    if not keys:
        print("!! No hay TOKEN_ENCRYPTION_KEY configurada; no puedo descifrar.")
        return
    cipher = TokenCipher(keys)

    # base_url de Moodle SIN el sufijo duplicado (settings ya lo trae completo,
    # acá recortamos para reconstruirlo una sola vez).
    base = settings.moodle_base_url
    if base.endswith("/webservice/rest/server.php"):
        base = base[: -len("/webservice/rest/server.php")]

    host = db_url.split("@")[-1].split("/")[0]
    print(f"BD  : {host}")
    print(f"KEYS: {len(keys)} configurada(s)")
    print(f"MOODLE: {base}\n")

    # Neon exige SSL; lo forzamos acá (sacamos sslmode de la URL arriba).
    engine = create_async_engine(db_url, connect_args={"ssl": True})
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select id, moodle_user_id, is_active, moodle_token "
                    "from users order by id"
                )
            )
        ).fetchall()

    print(f"Usuarios en la BD: {len(rows)}\n")
    for r in rows:
        raw = r.moodle_token or ""
        looks_fernet = raw.startswith("gAAAA")          # tiene pinta de ciphertext
        opens_with_current = cipher.is_encrypted(raw)     # la clave ACTUAL lo abre?
        plain = cipher.decrypt(raw)  # devuelve raw tal cual si no lo puede abrir
        looks_moodle = bool(_MOODLE_TOKEN_RE.match(plain))
        still_cipher = plain.startswith("gAAAA")          # abrió y aun asi es ciphertext

        # Clasificación del ESTADO EN LA BD (independiente de Moodle):
        if not raw:
            estado = "SIN TOKEN (columna vacía)"
        elif looks_fernet and not opens_with_current:
            estado = ("🔴 CIFRADO CON OTRA CLAVE — la clave actual NO lo abre. "
                      "ESTA es la causa: al scan se le mandó basura a Moodle.")
        elif opens_with_current and still_cipher:
            estado = ("🔴 DOBLE CIFRADO — la clave abre una capa y queda otro "
                      "ciphertext. Recuperable: descifrar de nuevo.")
        elif opens_with_current and looks_moodle:
            estado = "🟢 OK — cifrado con la clave actual y descifra a un token válido."
        elif looks_moodle:
            estado = "🟡 TEXTO PLANO (legacy sin cifrar) pero token con forma válida."
        else:
            estado = f"🟡 raro — descifrado no parece token de Moodle (len={len(plain)})."

        print(f"user_id={r.id} moodle_user_id={r.moodle_user_id} is_active={r.is_active}")
        print(f"  estado_en_bd: {estado}")
        print(f"  [debug] looks_fernet={looks_fernet} abre_con_clave_actual="
              f"{opens_with_current} forma_token_moodle={looks_moodle}")

        # Solo tiene sentido preguntarle a Moodle si lo que mandaríamos es un
        # token real; si es ciphertext, ya sabemos que lo rechazará.
        if looks_moodle:
            verdict = await _moodle_verdict(base, plain)
            print(f"  moodle -> {verdict}\n")
        else:
            print("  moodle -> (no consulto: lo que hay NO es un token usable)\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
