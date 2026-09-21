import httpx
from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.schemas import ErrorResponse, VehicleRequest, VehicleResponse

UPSTREAM_URL = "https://insurance-webhook-945894769129.us-central1.run.app/vehicle-info"
TIMEOUT = 10.0

router = APIRouter(
    prefix="/vehicle",
    tags=["vehicle"],
    dependencies=[Depends(require_api_key)],
)


def _error(error_code: str, message: str) -> dict:
    return {"success": False, "error_code": error_code, "message": message}


@router.post("/info", response_model=VehicleResponse | ErrorResponse)
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
