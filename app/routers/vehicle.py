import httpx
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.auth import require_api_key
from app.schemas import ErrorResponse, VehicleRequest, VehicleResponse

UPSTREAM_URL = "https://insurance-webhook-945894769129.us-central1.run.app/vehicle-info"
TIMEOUT = 10.0

# Each error code carries the HTTP status that matches its meaning, so callers
# can route on status and still read error_code to tell the failures apart.
ERROR_STATUS = {
    "invalid_license_plate": status.HTTP_400_BAD_REQUEST,
    "vehicle_not_found": status.HTTP_404_NOT_FOUND,
    "upstream_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "upstream_error": status.HTTP_502_BAD_GATEWAY,
}

router = APIRouter(
    prefix="/vehicle",
    tags=["vehicle"],
    dependencies=[Depends(require_api_key)],
)


def _error(error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=ERROR_STATUS[error_code],
        content={"success": False, "error_code": error_code, "message": message},
    )


@router.post(
    "/info",
    response_model=VehicleResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def vehicle_info(payload: VehicleRequest):
    plate = "".join(char for char in payload.license_plate if char.isdigit())

    if len(plate) not in (7, 8):
        return _error("invalid_license_plate", "License plate must be 7 or 8 digits.")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(UPSTREAM_URL, json={"license_plate": plate})
    except httpx.RequestError:
        return _error("upstream_unavailable", "The vehicle registry is not responding.")

    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        return _error("vehicle_not_found", f"No vehicle found for license plate {plate}.")
    if response.status_code in (400, 422):
        return _error("invalid_license_plate", "License plate must be 7 or 8 digits.")

    return _error("upstream_error", "The vehicle registry returned an unexpected error.")
