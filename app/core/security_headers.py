"""
Cabeceras de seguridad HTTP, aplicadas a toda respuesta de la API.

Usa un middleware ASGI puro en lugar de BaseHTTPMiddleware para evitar
problemas con CORS (BaseHTTPMiddleware puede tragarse las cabeceras
CORS en respuestas de error, causando "Network Error" en el navegador).
"""
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                extra_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
                ]
                if not settings.DEBUG:
                    extra_headers.append(
                        (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
                    )
                message["headers"] = list(message.get("headers", [])) + extra_headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
