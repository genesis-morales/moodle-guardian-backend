"""Migración one-shot: cifra los `moodle_token` que quedaron en texto plano.

Idempotente: los que ya están cifrados (Fernet válido) se saltan, así que se
puede correr varias veces sin daño. Requiere TOKEN_ENCRYPTION_KEY en el entorno.

Uso:
    python scripts/encrypt_existing_tokens.py

NUNCA loguea el valor del token.
"""

import asyncio
import logging

from sqlalchemy import select

from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.user_model import UserModel
from src.infrastructure.security.token_cipher import get_token_cipher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("encrypt_existing_tokens")


async def main() -> None:
    cipher = get_token_cipher()
    migrated = 0
    already = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserModel))
        models = result.scalars().all()

        for model in models:
            if not model.moodle_token or cipher.is_encrypted(model.moodle_token):
                already += 1
                continue
            model.moodle_token = cipher.encrypt(model.moodle_token)
            migrated += 1

        if migrated:
            await session.commit()

    logger.info(
        "Listo: %d token(s) cifrado(s), %d ya cifrado(s)/vacío(s), %d total.",
        migrated,
        already,
        len(models),
    )


if __name__ == "__main__":
    asyncio.run(main())
