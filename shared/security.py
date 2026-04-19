"""Simple shared-token auth for the FastAPI microservices.

Auth is deferred for single-user deployments (see plan). Every service still
verifies that callers carry the right SERVICE_TOKEN via the ``X-API-Key``
header. Swap this out for JWT when a multi-user phase begins.
"""

import os

from fastapi import Header, HTTPException, status


def verify_service_token(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    expected = os.getenv("SERVICE_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SERVICE_TOKEN is not set on the server",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
    return x_api_key
