from fastapi import APIRouter

from src.api.schemas.plans import ChannelResponse, PlanResponse, PlansResponse
from src.domain.entities.subscription_plan import CHANNEL_LABELS, PLANS

router = APIRouter(prefix="/v1/plans", tags=["Plans"])


@router.get("", response_model=PlansResponse)
async def list_plans() -> PlansResponse:
    """Catálogo de planes: fuente única para la landing y los forms de la web.

    La web pinta precios y qué canales muestra cada form desde aquí; el registro valida
    el `plan` recibido contra este mismo catálogo. Agregar/retocar un plan = editar
    `subscription_plan.py`, sin tocar la web ni la validación.
    """
    return PlansResponse(
        plans=[
            PlanResponse(
                key=plan.key,
                label=plan.label,
                price_crc=plan.price_crc,
                channels=[
                    ChannelResponse(key=channel, label=CHANNEL_LABELS[channel])
                    for channel in plan.channels
                ],
            )
            for plan in PLANS.values()
        ]
    )
