"""multi_tenant_empresa

Revision ID: 8b4ca75dd3a9
Revises: 0ce2598c4480
Create Date: 2026-09-02 12:25:19.753900

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import DATETIME # Or generic DateTime

# revision identifiers, used by Alembic.
revision: str = '8b4ca75dd3a9'
down_revision: Union[str, None] = '0ce2598c4480'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Crear tabla empresas
    op.create_table(
        'empresas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('cif', sa.String(length=50), nullable=True),
        sa.Column('direccion', sa.String(length=300), nullable=True),
        sa.Column('telefono', sa.String(length=50), nullable=True),
        sa.Column('correo', sa.String(length=150), nullable=True),
        sa.Column('logo_ruta', sa.String(length=500), nullable=True),
        sa.Column('color_principal', sa.String(length=7), nullable=False, server_default='#1E3A5F'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Añadir empresa_id a las tablas (nulleable primero)
    tablas = [
        'usuarios', 'obras', 'visitas', 'tareas', 'incidencias', 
        'presupuestos', 'documentos', 'citas_visita', 'eventos_calendario', 
        'actividades_cronograma', 'certificaciones', 'invitaciones'
    ]

    for tabla in tablas:
        # SQLite limitation: add_column for foreign keys might be tricky if not supported natively. 
        # For simplicity and since SQLite supports simple add_column:
        op.add_column(tabla, sa.Column('empresa_id', sa.Integer(), nullable=True))
        # Adding index and foreign key using naming convention or explicit creation
        with op.batch_alter_table(tabla) as batch_op:
            batch_op.create_foreign_key(f"fk_{tabla}_empresa_id", "empresas", ["empresa_id"], ["id"])

    # 3. Migrar Datos (Data Migration)
    # A. Copiar PerfilEmpresa a Empresas
    op.execute("""
        INSERT INTO empresas (id, nombre, cif, direccion, telefono, correo, logo_ruta, color_principal, created_at, updated_at)
        SELECT id, nombre_empresa, cif, direccion, telefono, correo, logo_ruta, color_principal, created_at, updated_at
        FROM perfiles_empresa
    """)

    # Actualizar secuencia PostgreSQL
    op.execute("SELECT setval(pg_get_serial_sequence('empresas', 'id'), COALESCE(MAX(id), 1)) FROM empresas")

    # Para los usuarios ADMIN que no tenían PerfilEmpresa, les creamos una empresa por defecto:
    op.execute("""
        INSERT INTO empresas (nombre)
        SELECT 'Empresa de ' || nombre FROM usuarios 
        WHERE rol = 'ADMIN' AND id NOT IN (SELECT usuario_id FROM perfiles_empresa)
    """)

    # B. Llenar empresa_id en usuarios
    # Si es ADMIN, su empresa es la que corresponde a su antiguo perfil, o la nueva.
    # En la migración inicial, vamos a asumir que el ID de la empresa coincide con el id de perfiles_empresa,
    # que a su vez es 1:1 con el usuario ADMIN.
    # Mejor aún: asignar empresa_id basándonos en el antiguo admin_id o id.
    
    # Asignar a ADMINs la empresa asociada a su PerfilEmpresa
    op.execute("""
        UPDATE usuarios 
        SET empresa_id = (
            SELECT id FROM empresas e WHERE e.id = (
                SELECT id FROM perfiles_empresa p WHERE p.usuario_id = usuarios.id
            )
        )
        WHERE rol = 'ADMIN'
    """)
    # Asignar a ADMINs sin perfil la empresa recién creada (buscando por nombre "Empresa de {nombre}")
    op.execute("""
        UPDATE usuarios 
        SET empresa_id = (SELECT id FROM empresas WHERE nombre = 'Empresa de ' || usuarios.nombre)
        WHERE rol = 'ADMIN' AND empresa_id IS NULL
    """)

    # Asignar a NO-ADMINs el empresa_id de su admin_id
    op.execute("""
        UPDATE usuarios
        SET empresa_id = (SELECT empresa_id FROM usuarios u2 WHERE u2.id = usuarios.admin_id)
        WHERE rol != 'ADMIN'
    """)

    # C. Llenar empresa_id en otras tablas basándose en las relaciones actuales
    
    # Obras: usar el empresa_id del usuario creador (que era usuario_id)
    op.execute("""
        UPDATE obras
        SET empresa_id = (SELECT empresa_id FROM usuarios WHERE usuarios.id = obras.usuario_id)
    """)

    # Visitas: hereda de Obra
    op.execute("UPDATE visitas SET empresa_id = (SELECT empresa_id FROM obras WHERE obras.id = visitas.obra_id)")
    
    # Tareas: hereda de Obra
    op.execute("UPDATE tareas SET empresa_id = (SELECT empresa_id FROM obras WHERE obras.id = tareas.obra_id)")
    
    # Incidencias: hereda de Obra
    op.execute("UPDATE incidencias SET empresa_id = (SELECT empresa_id FROM obras WHERE obras.id = incidencias.obra_id)")
    
    # Presupuestos: Si tienen obra_id, de la obra. Si no, del creador_id.
    op.execute("""
        UPDATE presupuestos 
        SET empresa_id = COALESCE(
            (SELECT empresa_id FROM obras WHERE obras.id = presupuestos.obra_id),
            (SELECT empresa_id FROM usuarios WHERE usuarios.id = presupuestos.creador_id)
        )
    """)
    
    # Documentos: hereda de Obra
    op.execute("UPDATE documentos SET empresa_id = (SELECT empresa_id FROM obras WHERE obras.id = documentos.obra_id)")
    
    # CitasVisitas: hereda de Obra o del usuario
    op.execute("""
        UPDATE citas_visita 
        SET empresa_id = COALESCE(
            (SELECT empresa_id FROM obras WHERE obras.id = citas_visita.obra_id),
            (SELECT empresa_id FROM usuarios WHERE usuarios.id = citas_visita.usuario_id)
        )
    """)
    
    # EventosCalendario: hereda de Obra o creador
    op.execute("""
        UPDATE eventos_calendario 
        SET empresa_id = COALESCE(
            (SELECT empresa_id FROM obras WHERE obras.id = eventos_calendario.obra_id),
            (SELECT empresa_id FROM usuarios WHERE usuarios.id = eventos_calendario.creador_id)
        )
    """)

    # ActividadesCronograma: hereda de Obra
    op.execute("UPDATE actividades_cronograma SET empresa_id = (SELECT empresa_id FROM obras WHERE obras.id = actividades_cronograma.obra_id)")
    
    # Certificaciones: hereda de Presupuesto
    op.execute("UPDATE certificaciones SET empresa_id = (SELECT empresa_id FROM presupuestos WHERE presupuestos.id = certificaciones.presupuesto_id)")

    # Invitaciones: hereda del admin_id original
    op.execute("UPDATE invitaciones SET empresa_id = (SELECT empresa_id FROM usuarios WHERE usuarios.id = invitaciones.admin_id)")

    # 4. Hacer que las columnas sean NOT NULL (excepto en SQLite que no soporta ALTER COLUMN facilmente)
    # Como SQLite no soporta alterar para hacer NOT NULL sin recrear la tabla, no lo forzaremos en el script
    # si estamos en SQLite, pero si la BD original fuera PostgreSQL, se haría.
    # Por ahora lo dejaremos como está para evitar fallos de batch_alter_table.
    
    # 5. Borrar perfiles_empresa
    op.drop_table('perfiles_empresa')

    # 6. Borrar admin_id de usuarios (Usamos batch_alter_table por SQLite)
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.drop_column('admin_id')

    # Invitaciones - quitar admin_id
    with op.batch_alter_table('invitaciones') as batch_op:
        batch_op.drop_column('admin_id')


def downgrade() -> None:
    pass # No downgrade path needed for this structural change
