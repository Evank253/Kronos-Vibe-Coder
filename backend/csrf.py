from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
import secrets


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow safe methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            resp = await call_next(request)
            return resp

        # For mutating requests, require X-CSRF-Token header matching session
        session = request.scope.get("session") or {}
        token = session.get("csrf_token")
        header = request.headers.get("x-csrf-token")
        if not token or not header or header != token:
            return JSONResponse(
                {"error": "CSRF token missing or invalid"}, status_code=403
            )

        return await call_next(request)


def ensure_csrf_in_session(session: dict):
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session
