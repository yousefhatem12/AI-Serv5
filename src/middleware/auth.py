from __future__ import annotations
from fastapi import Depends, Request
from src.core.security import verify_api_key, decode_access_token


async def get_current_user(
    request: Request,
    api_key: str | None = Depends(verify_api_key),
) -> dict:
    """
    Authenticates request via API Key or Bearer Token.
    Returns user dict or identifier.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = decode_access_token(token)
        if payload:
            return payload
    user_id = request.headers.get("x-user-id") or request.headers.get("x-client-id") or "authenticated_user"
    return {"user_id": user_id, "api_key": api_key}
