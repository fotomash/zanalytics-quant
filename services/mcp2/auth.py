import os
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def _get_expected_key() -> str:
    """Return expected API key from the environment."""
    return os.getenv("MCP2_API_KEY", "")


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(default=None),
) -> None:
    """Validate API key from Authorization or X-API-Key headers.

    If MCP2_API_KEY is unset or empty, auth is disabled.
    """
    expected = _get_expected_key()
    if not expected:
        return
    provided = credentials.credentials if credentials else x_api_key
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

