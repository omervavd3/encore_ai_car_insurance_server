import httpx
from fastapi import APIRouter, Depends, status

from app.auth import require_api_key
from app.errors import error_response
from app.schemas import ErrorResponse, VehicleRequest, VehicleResponse

UPSTREAM_URL = "https://insurance-webhook-945894769129.us-central1.run.app/vehicle-info"
TIMEOUT = 10.0

router = APIRouter(
    prefix="/vehicle",
    tags=["vehicle"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/info",
    response_model=VehicleResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def vehicle_info(payload: VehicleRequest):
    plate = "".join(char for char in payload.license_plate if char.isdigit())

    if len(plate) not in (7, 8):
        return error_response("invalid_license_plate", "License plate must be 7 or 8 digits.")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(UPSTREAM_URL, json={"license_plate": plate})
    except httpx.RequestError:
        return error_response("upstream_unavailable", "The vehicle registry is not responding.")

    if response.status_code == 200:
        # status_code is filled in by VehicleResponse's default; the upstream
        # body only carries success and data.
        return response.json()
    if response.status_code == 404:
        return error_response("vehicle_not_found", f"No vehicle found for license plate {plate}.")
    if response.status_code in (400, 422):
        return error_response("invalid_license_plate", "License plate must be 7 or 8 digits.")

    return error_response("upstream_error", "The vehicle registry returned an unexpected error.")
