"""Cifrado at-rest del `moodle_token`.

El token de Moodle es un secreto: si la DB se filtra, un token válido (vive
~3 meses) da acceso a la cuenta Moodle del estudiante. Lo ciframos at-rest con
Fernet (AES-128-CBC + HMAC) y lo mantenemos cifrado en la columna
`users.moodle_token`. El cifrado vive SOLO en la frontera con la DB
(`PostgresUserRepository`): el dominio siempre ve el token en claro.

Usamos `MultiFernet` para habilitar rotación de clave: la PRIMERA clave cifra,
TODAS descifran. Para rotar: se antepone la clave nueva, se re-cifran los tokens
(script de migración) y luego se quita la vieja.
"""

from functools import lru_cache
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from src.config.settings import get_settings
from src.domain.exceptions.domain_errors import TokenDecryptionError

logger = logging.getLogger(__name__)


class TokenCipher:
    """Cifra/descifra secretos con `MultiFernet` (soporta rotación de clave)."""

    # Todo ciphertext Fernet empieza con este prefijo (base64url del byte de
    # versión 0x80). Un token real de Moodle es 32 hex, nunca arranca con
    # 'g'/mayúsculas, así que sirve para distinguir "esto es un ciphertext" de
    # "esto es texto plano legacy".
    _FERNET_PREFIX = "gAAAA"

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError(
                "No hay clave de cifrado configurada. Definí TOKEN_ENCRYPTION_KEY. "
                'Generá una con: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        # La primera clave es la activa (cifra); todas descifran.
        self._fernet = MultiFernet([Fernet(key) for key in keys])

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            if ciphertext.startswith(self._FERNET_PREFIX):
                # Tiene forma de ciphertext Fernet pero NINGUNA clave lo abre:
                # es un problema de clave nuestra (rotación mal hecha, clave
                # equivocada/ausente), NO texto plano. Gritamos en vez de
                # devolver el ciphertext, que terminaría viajando a Moodle
                # disfrazado de token → falso `invalidtoken`. Nunca logueamos el
                # valor.
                raise TokenDecryptionError(
                    "No se pudo descifrar un moodle_token con forma de ciphertext "
                    "Fernet: revisar TOKEN_ENCRYPTION_KEY (¿clave equivocada, o "
                    "rotación sin dejar la clave vieja en la lista?)."
                )
            # Token heredado en texto plano (aún no migrado por
            # scripts/encrypt_existing_tokens.py). Lo devolvemos tal cual para
            # no romper la operación durante la transición. NUNCA logueamos el
            # valor. Este fallback se puede quitar una vez migrados todos.
            logger.warning(
                "moodle_token en texto plano (legacy): correr "
                "scripts/encrypt_existing_tokens.py para cifrarlo."
            )
            return ciphertext

        if plaintext.startswith(self._FERNET_PREFIX):
            # Descifró una capa pero el resultado sigue siendo ciphertext Fernet:
            # el token quedó doble-cifrado. Tampoco es usable; hay que descifrar
            # la capa extra (re-guardar) antes de usarlo.
            raise TokenDecryptionError(
                "moodle_token doble-cifrado: descifrar la capa extra "
                "(re-guardar) antes de usarlo."
            )
        return plaintext

    def is_encrypted(self, value: str) -> bool:
        """True si `value` es un ciphertext Fernet válido de alguna de las claves.

        Lo usa el script de migración para ser idempotente (no re-cifrar lo ya
        cifrado). No confiar en el prefijo `gAAAA`: verifica el HMAC.
        """
        try:
            self._fernet.decrypt(value.encode())
            return True
        except InvalidToken:
            return False


@lru_cache
def get_token_cipher() -> TokenCipher:
    """Cipher singleton construido desde settings (claves en env)."""
    return TokenCipher(get_settings().token_encryption_keys)
