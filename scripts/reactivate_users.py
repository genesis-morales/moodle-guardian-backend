"""Reactiva usuarios (is_active=True) por moodle_user_id, con red de seguridad.

Antes de reactivar, RE-VERIFICA que el token descifre y siga VIVO en Moodle,
para no revivir a alguien con un token realmente muerto. NUNCA imprime el token.

Uso (dry-run: solo lista los inactivos y no toca nada):
    PROD_DATABASE_URL='...' python scripts/reactivate_users.py

Uso (reactiva los indicados):
    PROD_DATABASE_URL='...' python scripts/reactivate_users.py 3095 4327
"""

import asyncio
import os
import re
import sys

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings  # noqa: E402
from src.infrastructure.security.token_cipher import TokenCipher  # noqa: E402

_MOODLE_TOKEN_RE = re.compile(r"^[a-f0-9]{32}$")


def _normalize_async(url: str) -> str:
    url = url.split("?", 1)[0]
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


async def _token_alive(base_url: str, token: str) -> bool:
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
    except Exception:  # noqa: BLE001
        return False
    return isinstance(data, dict) and "userid" in data


async def main() -> None:
    settings = get_settings()
    db_url = _normalize_async(os.environ.get("PROD_DATABASE_URL") or settings.database_url)
    targets = {int(a) for a in sys.argv[1:] if a.isdigit()}

    keys = settings.token_encryption_keys
    if not keys:
        print("!! No hay TOKEN_ENCRYPTION_KEY; no puedo verificar tokens.")
        return
    cipher = TokenCipher(keys)

    base = settings.moodle_base_url
    if base.endswith("/webservice/rest/server.php"):
        base = base[: -len("/webservice/rest/server.php")]

    engine = create_async_engine(db_url, connect_args={"ssl": True})
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("select id, moodle_user_id, is_active, moodle_token "
                     "from users where is_active = false order by id")
            )
        ).fetchall()

    if not rows:
        print("No hay usuarios inactivos. Nada que hacer.")
        await engine.dispose()
        return

    if not targets:
        print("Usuarios INACTIVOS (dry-run, no toco nada):")
        for r in rows:
            print(f"  moodle_user_id={r.moodle_user_id} (user_id={r.id})")
        print("\nPara reactivar, pasá sus moodle_user_id como argumentos, ej.:")
        print(f"  python scripts/reactivate_users.py "
              f"{' '.join(str(r.moodle_user_id) for r in rows)}")
        await engine.dispose()
        return

    to_activate = []
    for r in rows:
        if r.moodle_user_id not in targets:
            continue
        plain = cipher.decrypt(r.moodle_token or "")
        if not _MOODLE_TOKEN_RE.match(plain):
            print(f"⏭  moodle_user_id={r.moodle_user_id}: token no descifra a algo "
                  f"válido; NO lo reactivo.")
            continue
        if not await _token_alive(base, plain):
            print(f"⏭  moodle_user_id={r.moodle_user_id}: token MUERTO en Moodle; "
                  f"NO lo reactivo (necesita relink).")
            continue
        to_activate.append(r.moodle_user_id)
        print(f"✅ moodle_user_id={r.moodle_user_id}: token vivo → se reactivará.")

    if not to_activate:
        print("\nNinguno cumple las condiciones para reactivar.")
        await engine.dispose()
        return

    async with engine.begin() as conn:
        await conn.execute(
            text("update users set is_active = true "
                 "where moodle_user_id = any(:ids)"),
            {"ids": to_activate},
        )
    print(f"\nListo: reactivados {len(to_activate)} usuario(s): {to_activate}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
