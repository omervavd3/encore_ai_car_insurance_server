from typing import Literal

from pydantic import BaseModel


class VehicleRequest(BaseModel):
    license_plate: str


class Vehicle(BaseModel):
    license_plate: str
    manufacturer: str
    model: str
    year: int
    color: str


class VehicleResponse(BaseModel):
    success: Literal[True] = True
    data: Vehicle


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error_code: Literal[
        "invalid_license_plate",
        "vehicle_not_found",
        "upstream_unavailable",
        "upstream_error",
    ]
    message: str
