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


async def enviar_recordatorio_cita(usuario: Usuario, cita: CitaVisita) -> None:
    referencia = cita.obra_id or cita.nombre_referencia
    # TODO (Fase B): sustituir este log por el envío real vía FCM,
    # usando los tokens de dispositivo registrados del usuario.
    logger.info(
        "[RECORDATORIO] Usuario %s (%s) — cita #%s (%s) programada para %s",
        usuario.id,
        usuario.email,
        cita.id,
        referencia,
        cita.fecha_hora.isoformat(),
    )
