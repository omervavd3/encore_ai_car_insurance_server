from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.errors import APIError, error_response
from app.routers import vehicle

app = FastAPI(title="Vehicle Info API")


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return error_response(exc.error_code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # FastAPI's default body for a malformed request is {"detail": [...]},
    # which is the one shape a client couldn't parse like the rest.
    return error_response("invalid_request", "Request body is malformed or incomplete.")


app.include_router(vehicle.router)


@app.get("/health")
async def health():
    return {"status": "ok", "status_code": 200}
