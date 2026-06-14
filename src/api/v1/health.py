from fastapi import APIRouter, status, Response

router = APIRouter(prefix="/v1/health", tags=["Health"])

@router.api_route("", methods=["GET", "HEAD"], status_code=status.HTTP_200_OK, include_in_schema=False)
async def healthcheck() -> Response:
    return Response(content='{"status":"ok"}', media_type="application/json")