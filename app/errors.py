from fastapi import status
from fastapi.responses import JSONResponse

# Each error code carries the HTTP status that matches its meaning, so callers
# can route on status and still read error_code to tell the failures apart.
ERROR_STATUS = {
    "unauthorized": status.HTTP_401_UNAUTHORIZED,
    "invalid_request": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "invalid_license_plate": status.HTTP_400_BAD_REQUEST,
    "vehicle_not_found": status.HTTP_404_NOT_FOUND,
    "upstream_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "upstream_error": status.HTTP_502_BAD_GATEWAY,
}


class APIError(Exception):
    """Error envelope raised from places that can't return a response directly.

    Dependencies are the main case: require_api_key has to raise, not return,
    so main.py turns this back into the same JSON body the routes produce.
    """

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def error_response(error_code: str, message: str) -> JSONResponse:
    # The HTTP status and the status_code field are read from one lookup, so a
    # response can never report one status in the headers and another in the body.
    status_code = ERROR_STATUS[error_code]
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status_code": status_code,
            "error_code": error_code,
            "message": message,
        },
    )
