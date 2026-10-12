import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.presupuesto import Presupuesto, EstadoPresupuesto
from app.models.empresa import Empresa
from app.schemas.presupuesto import (
    CapituloPresupuestoCreate,
    PartidaPresupuestoCreate,
    PartidaPresupuestoUpdate,
    LineaMedicionCreate,
    LineaMedicionUpdate,
)
from app.services.presupuesto_service import (
    crear_capitulo,
    crear_partida,
    actualizar_partida,
    eliminar_partida,
    crear_linea_medicion,
    actualizar_linea_medicion,
    eliminar_linea_medicion,
    eliminar_capitulo,
)

@pytest.mark.asyncio
async def test_presupuesto_crud_operations(db_session: AsyncSession):
    # 1. Crear Empresa
    empresa = Empresa(nombre="Empresa Test", cif="B12345678")
    db_session.add(empresa)
    await db_session.commit()
    await db_session.refresh(empresa)

    # 2. Crear Presupuesto
    presupuesto = Presupuesto(
        nombre="Presupuesto Test",
        codigo="PTO-2026-001",
        iva=21.0,
        estado=EstadoPresupuesto.BORRADOR,
        empresa_id=empresa.id
    )
    db_session.add(presupuesto)
    await db_session.commit()
    await db_session.refresh(presupuesto)

    # 3. Crear Capitulo
    capitulo = await crear_capitulo(
        db_session,
        presupuesto.id,
        CapituloPresupuestoCreate(nombre="01 DEMOLICIONES", orden=0),
        empresa.id
    )
    assert capitulo.id is not None
    assert capitulo.nombre == "01 DEMOLICIONES"

    # 4. Crear Partida
    partida = await crear_partida(
        db_session,
        capitulo.id,
        PartidaPresupuestoCreate(
            codigo="01.01",
            descripcion="Demolición de tabiquería",
            unidad="M2",
            cantidad=100.0,
            precio_unitario=15.5
        ),
        empresa.id
    )
    assert partida.id is not None
    assert partida.codigo == "01.01"

    # 5. Actualizar Partida (This was the failing operation in the user's report!)
    partida_actualizada = await actualizar_partida(
        db_session,
        partida.id,
        PartidaPresupuestoUpdate(
            descripcion="Demolición de tabiquería y retirada de escombros",
            cantidad=120.0,
            precio_unitario=18.0,
            coste_base=10.0,
            coste_material=2.0,
            porcentaje_indirectos=15.0
        ),
        empresa.id
    )
    assert partida_actualizada.cantidad == 120.0
    assert partida_actualizada.precio_unitario == 18.0
    assert partida_actualizada.descripcion == "Demolición de tabiquería y retirada de escombros"

    # 6. Crear Línea de Medición
    medicion = await crear_linea_medicion(
        db_session,
        partida.id,
        LineaMedicionCreate(
            comentario="Zona salón",
            unidades=1,
            longitud=10.0,
            anchura=5.0,
            altura=2.5
        ),
        empresa.id
    )
    assert medicion.id is not None
    assert medicion.longitud == 10.0

    # 7. Actualizar Línea de Medición
    medicion_actualizada = await actualizar_linea_medicion(
        db_session,
        medicion.id,
        LineaMedicionUpdate(
            comentario="Zona salón ampliada",
            longitud=12.0
        ),
        empresa.id
    )
    assert medicion_actualizada.longitud == 12.0
    assert medicion_actualizada.comentario == "Zona salón ampliada"

    # 8. Eliminar Línea de Medición
    del_med_res = await eliminar_linea_medicion(db_session, medicion.id, empresa.id)
    assert del_med_res["message"] == "Línea de medición eliminada"

    # 9. Eliminar Partida
    del_part_res = await eliminar_partida(db_session, partida.id, empresa.id)
    assert del_part_res["message"] == "Partida eliminada"

    # 10. Eliminar Capítulo
    del_cap_res = await eliminar_capitulo(db_session, capitulo.id, empresa.id)
    assert del_cap_res["message"] == "Capítulo eliminado"
