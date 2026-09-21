import os
import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.errors import APIError

API_KEY = os.getenv("API_KEY", "")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(provided_key: str | None = Security(api_key_header)) -> None:
    if not API_KEY or not provided_key or not secrets.compare_digest(provided_key, API_KEY):
        # APIError rather than HTTPException so the 401 body carries the same
        # success / status_code / error_code envelope as every other failure.
        raise APIError("unauthorized", "Invalid or missing API key.")
