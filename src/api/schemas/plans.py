from pydantic import BaseModel


class ChannelResponse(BaseModel):
    key: str    # clave estable del canal ("telegram", "email", ...)
    label: str  # etiqueta para la UI ("Telegram", "Correo", ...)


class PlanResponse(BaseModel):
    key: str
    label: str
    price_crc: int
    channels: list[ChannelResponse]  # canales PERMITIDOS por el plan (techo)


class PlansResponse(BaseModel):
    plans: list[PlanResponse]
