from fastapi import APIRouter

router = APIRouter(prefix="/v1/health", tags=["Health"])


@router.get("")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}