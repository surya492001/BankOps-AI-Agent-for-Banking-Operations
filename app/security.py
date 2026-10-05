"""Shared-secret protection for the API."""

import hmac
import os

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Reject requests that do not carry the configured `API_KEY`.

    When `API_KEY` is not set the API is open, which suits local use and the
    tests. A deployed API sets it, and the dashboard sends it in the
    `X-API-Key` header, so only the dashboard can use the API and spend the
    LLM key.
    """
    expected = os.getenv("API_KEY")
    if not expected:
        return

    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
