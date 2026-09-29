import logging
from app.config import settings
from app.models.usuario import Usuario
from app.models.obra import Obra

logger = logging.getLogger(__name__)

class EmailService:
    """
    Abstracción central para el envío de correos.
    Nadie fuera de esta clase debe interactuar con Resend.
    """
    
    @staticmethod
    async def enviar_correo(
        destinatario: str, 
        asunto: str, 
        template_name: str, 
        context: dict
    ) -> bool:
        if not settings.RESEND_API_KEY:
            logger.warning(f"No hay API Key de Resend. Simulando envío a {destinatario}: {asunto}")
            return False
            
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            
            # TODO: Implementar renderizado real con Jinja2 o similar.
            # Por ahora usamos un texto plano / html básico.
            html_content = f"<p>Este es un correo del sistema DIAM. Plantilla: {template_name}</p>"
            
            params = {
                "from": settings.FROM_EMAIL or "onboarding@resend.dev",
                "to": [destinatario],
                "subject": asunto,
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Correo enviado a {destinatario}. ID: {response.get('id')}")
            return True
        except Exception as e:
            logger.error(f"Error enviando correo a {destinatario}: {e}")
            return False

    @classmethod
    async def notificar_nueva_obra(cls, usuario: Usuario, obra: Obra):
        await cls.enviar_correo(
            destinatario=usuario.email,
            asunto=f"Nueva obra creada: {obra.nombre}",
            template_name="nueva_obra",
            context={"obra_nombre": obra.nombre, "usuario_nombre": usuario.nombre}
        )

    @classmethod
    async def enviar_invitacion(cls, email_destino: str, empresa_nombre: str, token: str):
        await cls.enviar_correo(
            destinatario=email_destino,
            asunto=f"Invitación para unirte a {empresa_nombre} en DIAM",
            template_name="invitacion",
            context={"empresa_nombre": empresa_nombre, "token": token}
        )
