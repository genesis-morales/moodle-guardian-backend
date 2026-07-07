class DomainError(Exception):
    """Error de dominio genérico."""
    pass


class MoodleTokenError(DomainError):
    """El token de Moodle del usuario es inválido o expiró (errorcode
    `invalidtoken`).

    A diferencia de un fallo transitorio (red, timeout), esto NO se resuelve
    reintentando: el token fue revocado/borrado y requiere que el usuario
    vuelva a vincularlo. El scan lo trata aparte para desactivar al usuario en
    lugar de reintentar indefinidamente en cada corrida.
    """
    pass


class MoodleFeatureDisabledError(DomainError):
    """Una función del web service está deshabilitada en el sitio (errorcode
    `disabled`), p.ej. la mensajería (`core_message_get_conversations` cuando el
    admin apagó `$CFG->messaging`).

    NO es un fallo del token ni transitorio: no se arregla reintentando ni
    revinculando. Como se dispara sobre fuentes OPCIONALES (mensajes), el scan la
    trata como degradación con gracia — omite esa fuente y sigue con el resto del
    snapshot — en vez de tumbar toda la corrida de la conexión.
    """
    pass


class TokenDecryptionError(DomainError):
    """No se pudo descifrar un `moodle_token` que SÍ tiene forma de ciphertext
    Fernet (o quedó doble-cifrado).

    Es un problema de CLAVE nuestra (rotación mal hecha, `TOKEN_ENCRYPTION_KEY`
    equivocada o ausente), NO del token del usuario: el token puede estar
    perfecto. Por eso NO hereda de `MoodleTokenError` y el scan NO debe
    desactivar al usuario por esto — debe ser ruidoso (Sentry) para que lo
    arreglemos nosotros, en vez de mandar el ciphertext a Moodle como si fuera
    el token (que se disfrazaría de `invalidtoken`).
    """
    pass