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