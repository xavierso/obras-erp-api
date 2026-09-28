"""
Servicio de notificaciones.

Ahora mismo NO envía nada de verdad (no hay app móvil todavía, así que no
hay tokens de dispositivo que notificar). Sirve como punto de enganche
único: cuando en la Fase B se registren tokens de Firebase Cloud Messaging
por usuario, solo hay que implementar el cuerpo de esta función — el
scheduler y el resto de la API no necesitan cambiar.
"""
import logging

from app.models.cita_visita import CitaVisita
from app.models.usuario import Usuario

logger = logging.getLogger("notificaciones")


from app.services.email_service import enviar_email

async def enviar_recordatorio_cita(usuario: Usuario, cita: CitaVisita) -> None:
    referencia = cita.obra_id or cita.nombre_referencia
    logger.info(
        "[RECORDATORIO] Usuario %s (%s) — cita #%s (%s) programada para %s",
        usuario.id,
        usuario.email,
        cita.id,
        referencia,
        cita.fecha_hora.isoformat(),
    )
    
    asunto = f"Recordatorio de visita: {referencia}"
    html = f"""
    <h2>Recordatorio de cita</h2>
    <p>Tienes una visita programada próximamente para la referencia/obra: <strong>{referencia}</strong>.</p>
    <p>Fecha y hora: {cita.fecha_hora.isoformat()}</p>
    <br/>
    <p>Por favor revisa el sistema para más detalles.</p>
    """
    
    await enviar_email(usuario.email, asunto, html)
