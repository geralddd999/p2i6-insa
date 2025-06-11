from fastapi import Header, HTTPException, status, Query
import os

API_TOKEN = os.getenv("API_TOKEN", "very-secret-and-difficult-token")

async def verify_token(
    authorization: str | None = Header(None),
    token: str | None = Query(None),
) -> None:
    """
    Accept Bearer token in *either* the Authorization header
    or a `?token=…` query parameter (convenient for HTML links).
    """
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization.split()[1]
    elif token:
        supplied = token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    if supplied != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token",
        )