"""
Lógica de invitaciones de equipo.

Igual que notificacion_service.py: el envío real de email no está
implementado (no hay proveedor de correo configurado todavía). Por ahora
se genera el token y se deja logueado / devuelto en la respuesta del
endpoint, para que puedas probarlo a mano mientras no haya email real.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

DIAS_VALIDEZ_INVITACION = 7

logger = logging.getLogger("invitaciones")


def generar_token() -> str:
    return secrets.token_urlsafe(32)


def calcular_expiracion() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=DIAS_VALIDEZ_INVITACION)


async def enviar_email_invitacion(email: str, token: str, nombre_admin: str) -> None:
    # TODO: sustituir por envío real (ej. Resend, SendGrid, SES) cuando
    # haya un proveedor de email configurado.
    logger.info(
        "[INVITACIÓN] %s ha sido invitado por %s. Token: %s",
        email,
        nombre_admin,
        token,
    )
