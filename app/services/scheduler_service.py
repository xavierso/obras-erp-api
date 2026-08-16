"""
Scheduler de recordatorios, migrado del job periódico del bot (cada 5 min).

Diseño idéntico en espíritu al del bot: NO depende de temporizadores en
memoria por cada cita (esos morirían al reiniciar el proceso). En vez de
eso, cada 5 minutos se hace una consulta a la base de datos por citas cuyo
momento_recordatorio ya pasó y aún no se han notificado — así el sistema
sobrevive a reinicios del servidor sin perder ni duplicar recordatorios.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.cita_visita import CitaVisita, EstadoCita
from app.models.usuario import Usuario
from app.services.notificacion_service import enviar_recordatorio_cita

logger = logging.getLogger("scheduler")

INTERVALO_MINUTOS = 5


async def revisar_recordatorios_pendientes() -> None:
    async with AsyncSessionLocal() as db:
        ahora = datetime.now(timezone.utc)

        result = await db.execute(
            select(CitaVisita).where(
                CitaVisita.estado == EstadoCita.PENDIENTE,
                CitaVisita.recordatorio_enviado.is_(False),
                CitaVisita.momento_recordatorio.is_not(None),
                CitaVisita.momento_recordatorio <= ahora,
            )
        )
        citas_pendientes = result.scalars().all()

        if not citas_pendientes:
            return

        for cita in citas_pendientes:
            result_usuario = await db.execute(
                select(Usuario).where(Usuario.id == cita.usuario_id)
            )
            usuario = result_usuario.scalar_one_or_none()
            if usuario is None:
                continue

            try:
                await enviar_recordatorio_cita(usuario, cita)
                cita.recordatorio_enviado = True
            except Exception:
                # Si falla el envío, NO marcamos como enviado -> se reintenta
                # en la siguiente pasada del scheduler (5 min después).
                logger.exception("Fallo al enviar recordatorio de cita #%s", cita.id)

        await db.commit()


_scheduler: AsyncIOScheduler | None = None


def iniciar_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        revisar_recordatorios_pendientes,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="revisar_recordatorios",
        replace_existing=True,
        misfire_grace_time=60,
    )
    _scheduler.start()
    logger.info("Scheduler de recordatorios iniciado (cada %s min)", INTERVALO_MINUTOS)
    return _scheduler


def detener_scheduler() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
