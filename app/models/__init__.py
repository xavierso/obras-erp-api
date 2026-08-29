"""
Se importan aquí todos los modelos para que SQLAlchemy resuelva
correctamente las relationships al llamar a Base.metadata.create_all()
o al generar migraciones con Alembic.
"""
from app.models.usuario import Usuario, RolUsuario
from app.models.obra import Obra, EstadoObra
from app.models.visita import Visita, VisitaArchivo, TipoArchivoVisita
from app.models.documento import Documento, CategoriaDocumento
from app.models.perfil_empresa import PerfilEmpresa
from app.models.cita_visita import CitaVisita, EstadoCita
from app.models.visita_potencial import VisitaPotencial, VisitaPotencialArchivo
from app.models.invitacion import Invitacion, EstadoInvitacion
from app.models.tarea import Tarea, HistorialTarea, EstadoTarea
from app.models.incidencia import Incidencia, HistorialIncidencia, EstadoIncidencia, IncidenciaArchivo
from app.models.evento_calendario import EventoCalendario, TipoEventoCalendario, EstadoEventoCalendario
from app.models.actividad_cronograma import ActividadCronograma, EstadoActividad
from app.models.presupuesto import Presupuesto, CapituloPresupuesto, PartidaPresupuesto, EstadoPresupuesto
from app.models.certificacion import Certificacion, LineaCertificacion, EstadoCertificacion

__all__ = [
    "Usuario",
    "RolUsuario",
    "Obra",
    "EstadoObra",
    "Visita",
    "VisitaArchivo",
    "TipoArchivoVisita",
    "Documento",
    "CategoriaDocumento",
    "PerfilEmpresa",
    "CitaVisita",
    "EstadoCita",
    "VisitaPotencial",
    "VisitaPotencialArchivo",
    "Invitacion",
    "EstadoInvitacion",
    "Tarea",
    "HistorialTarea",
    "EstadoTarea",
    "Incidencia",
    "HistorialIncidencia",
    "EstadoIncidencia",
    "IncidenciaArchivo",
    "EventoCalendario",
    "TipoEventoCalendario",
    "EstadoEventoCalendario",
    "ActividadCronograma",
    "EstadoActividad",
    "Presupuesto",
    "EstadoPresupuesto",
    "CapituloPresupuesto",
    "PartidaPresupuesto",
    "Certificacion",
    "LineaCertificacion",
    "EstadoCertificacion",
]
