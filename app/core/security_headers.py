"""
Cabeceras de seguridad HTTP, aplicadas a toda respuesta de la API.

No sustituyen a HTTPS en producción (eso lo gestiona el servidor/proxy
delante de uvicorn, ej. Nginx o el balanceador del hosting), pero
reducen superficie de ataque del lado del navegador (para /docs, para
cualquier panel web futuro, y para los archivos servidos en /files).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS solo tiene sentido si de verdad se sirve por HTTPS (en
        # DEBUG/desarrollo local por HTTP, mandarlo rompería pruebas).
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )

        return response
