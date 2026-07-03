class RegistrationError(Exception):
    pass


class RelinkUserNotFoundError(Exception):
    """El usuario a re-vincular no existe (re-vincular ≠ registrar)."""
    pass