"""Catálogo de planes de suscripción (tier + canales permitidos).

Fuente ÚNICA de verdad de los planes: la landing y los forms de la web se pintan desde
`GET /v1/plans`, y la validación del registro usa este mismo catálogo (nada hardcodeado en
dos lados). Igual que `moodle_site.py`, hoy es dato-en-código para migrar a una tabla DB sin
reescribir cuando haya pricing dinámico.

Dos distinciones que importan y que en el lenguaje de negocio van mezcladas:

1. `email` (identidad de cuenta) es SIEMPRE requerido, en cualquier plan (incluido Alerta
   gratis). Es la llave de login/pago, NO un canal. El canal `email` de este catálogo es el
   **correo como sink de notificación** (Escudo/Guardian). Coinciden en valor pero son cosas
   distintas.
2. El `plan` es un **techo**: define el conjunto de canales PERMITIDOS. Qué canales activa de
   verdad la cuenta (un subconjunto ⊆ plan) es preferencia del usuario y se modela en feat 3.
   Por ahora solo se persiste el tier elegido; el gating por canal/pago es downstream.
"""

from dataclasses import dataclass

# Canales/sinks de entrega. Claves estables (viajan en el API); labels para pintar la web.
CHANNEL_TELEGRAM = "telegram"
CHANNEL_EMAIL = "email"        # correo como sink de notificación (≠ email identidad)
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_CALENDAR = "calendar"  # Google Calendar (sink, feat 4)
CHANNEL_NOTION = "notion"      # Notion (sink, feat 4)

CHANNEL_LABELS: dict[str, str] = {
    CHANNEL_TELEGRAM: "Telegram",
    CHANNEL_EMAIL: "Correo",
    CHANNEL_WHATSAPP: "WhatsApp",
    CHANNEL_CALENDAR: "Google Calendar",
    CHANNEL_NOTION: "Notion",
}


@dataclass(frozen=True)
class SubscriptionPlan:
    key: str                    # identificador estable, viaja en `plan` ("alerta")
    label: str                  # nombre visible ("Alerta")
    price_crc: int              # precio mensual en colones (0 = gratis)
    channels: tuple[str, ...]   # canales PERMITIDOS (techo); el orden = orden de UI


PLANS: dict[str, SubscriptionPlan] = {
    "alerta": SubscriptionPlan(
        key="alerta",
        label="Alerta",
        price_crc=0,
        channels=(CHANNEL_TELEGRAM,),
    ),
    "escudo": SubscriptionPlan(
        key="escudo",
        label="Escudo",
        price_crc=2000,
        channels=(CHANNEL_TELEGRAM, CHANNEL_EMAIL, CHANNEL_CALENDAR),
    ),
    "guardian": SubscriptionPlan(
        key="guardian",
        label="Guardián",
        price_crc=4000,
        channels=(
            CHANNEL_WHATSAPP,
            CHANNEL_TELEGRAM,
            CHANNEL_EMAIL,
            CHANNEL_CALENDAR,
            CHANNEL_NOTION,
        ),
    ),
}

# A diferencia de moodle_site (donde ningún campus es default), acá el free tier SÍ es un
# default de producto legítimo: registrarse sin plan = Alerta gratis.
DEFAULT_PLAN_KEY = "alerta"


class UnknownPlanError(ValueError):
    """El plan no existe en el catálogo."""


def get_plan(plan_key: str) -> SubscriptionPlan:
    """Devuelve el plan del catálogo o falla claro si el key no existe."""
    plan = PLANS.get(plan_key)
    if plan is None:
        raise UnknownPlanError(
            f"plan '{plan_key}' desconocido; válidos: {sorted(PLANS)}"
        )
    return plan


def is_valid_plan(plan_key: str) -> bool:
    return plan_key in PLANS


def plan_allows(plan_key: str, channel: str) -> bool:
    """¿El plan permite ese canal? Base para el gating por canal (feat 3)."""
    return channel in get_plan(plan_key).channels
