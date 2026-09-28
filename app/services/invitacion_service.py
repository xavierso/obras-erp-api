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


from app.services.email_service import enviar_email

async def enviar_email_invitacion(email: str, token: str, nombre_admin: str) -> None:
    logger.info(
        "[INVITACIÓN] %s ha sido invitado por %s. Token: %s",
        email,
        nombre_admin,
        token,
    )
    
    asunto = f"Has sido invitado a unirte a Obras ERP por {nombre_admin}"
    html = f"""
    <h2>¡Hola!</h2>
    <p>{nombre_admin} te ha invitado a formar parte de su equipo en Obras ERP.</p>
    <p>Para aceptar la invitación y configurar tu cuenta, utiliza el siguiente token de acceso en el sistema de registro:</p>
    <p><strong>{token}</strong></p>
    <br/>
    <p>Este token expirará en {DIAS_VALIDEZ_INVITACION} días.</p>
    """
    
    await enviar_email(email, asunto, html)
