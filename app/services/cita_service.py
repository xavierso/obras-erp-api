"""
Lógica de negocio de CitaVisita, migrada desde bot_erp_obras.
"""
from datetime import datetime, timedelta


def calcular_momento_recordatorio(
    fecha_hora: datetime, minutos_antes: int | None
) -> datetime | None:
    """
    Devuelve el instante exacto en el que debe dispararse el recordatorio,
    o None si la cita no tiene recordatorio configurado.
    """
    if minutos_antes is None:
        return None
    return fecha_hora - timedelta(minutes=minutos_antes)
