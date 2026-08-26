import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.models.usuario import Usuario
from app.models.cita_visita import CitaVisita, EstadoCita
from app.models.visita_potencial import VisitaPotencial

@pytest.fixture
async def test_cita(db_session: AsyncSession, test_user: Usuario) -> CitaVisita:
    cita = CitaVisita(
        usuario_id=test_user.id,
        nombre_referencia="Referencia de prueba",
        fecha_hora=datetime.now(timezone.utc) + timedelta(days=1),
        estado=EstadoCita.PENDIENTE
    )
    db_session.add(cita)
    await db_session.commit()
    await db_session.refresh(cita)
    return cita

@pytest.fixture
async def test_visita_potencial(db_session: AsyncSession, test_cita: CitaVisita) -> VisitaPotencial:
    visita = VisitaPotencial(
        cita_id=test_cita.id,
        usuario_id=test_cita.usuario_id,
        descripcion="Visita potencial de prueba"
    )
    db_session.add(visita)
    await db_session.commit()
    await db_session.refresh(visita)
    return visita


@pytest.mark.asyncio
async def test_registrar_visita_potencial_sin_archivos(
    auth_client: AsyncClient, test_cita: CitaVisita
):
    response = await auth_client.post(
        f"/citas/{test_cita.id}/visitas-potenciales",
        data={"descripcion": "Prueba de visita potencial"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["cita_id"] == test_cita.id
    assert data["descripcion"] == "Prueba de visita potencial"
    assert len(data["archivos"]) == 0

@pytest.mark.asyncio
@patch("app.routers.visitas_potenciales.guardar_archivo")
async def test_registrar_visita_potencial_con_archivos(
    mock_guardar_archivo,
    auth_client: AsyncClient, 
    test_cita: CitaVisita
):
    # Setup mock
    mock_guardar_archivo.return_value = ("citas/1/visitas-potenciales/1/test.jpg", "test.jpg")
    
    # Preparamos un archivo de mentira (dummy)
    files = [
        ("archivos", ("test.jpg", b"fake image content", "image/jpeg"))
    ]
    data = {"descripcion": "Prueba con foto"}

    response = await auth_client.post(
        f"/citas/{test_cita.id}/visitas-potenciales",
        data=data,
        files=files
    )
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["descripcion"] == "Prueba con foto"
    assert len(res_data["archivos"]) == 1
    assert res_data["archivos"][0]["nombre_original"] == "test.jpg"
    assert mock_guardar_archivo.called

@pytest.mark.asyncio
async def test_listar_visitas_potenciales(
    auth_client: AsyncClient, test_cita: CitaVisita, test_visita_potencial: VisitaPotencial
):
    response = await auth_client.get(f"/citas/{test_cita.id}/visitas-potenciales")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == test_visita_potencial.id

@pytest.mark.asyncio
@patch("app.routers.visitas_potenciales.generar_parte_trabajo_pdf")
async def test_generar_parte_de_trabajo(
    mock_generar_pdf,
    auth_client: AsyncClient, 
    test_cita: CitaVisita, 
    test_visita_potencial: VisitaPotencial
):
    mock_generar_pdf.return_value = b"%PDF-1.4 Fake PDF Content"
    
    response = await auth_client.get(
        f"/citas/{test_cita.id}/visitas-potenciales/{test_visita_potencial.id}/parte-trabajo"
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.content == b"%PDF-1.4 Fake PDF Content"
    assert mock_generar_pdf.called

@pytest.mark.asyncio
async def test_registrar_visita_potencial_cita_inexistente(
    auth_client: AsyncClient
):
    response = await auth_client.post(
        "/citas/999/visitas-potenciales",
        data={"descripcion": "Prueba"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_generar_parte_trabajo_visita_inexistente(
    auth_client: AsyncClient, test_cita: CitaVisita
):
    response = await auth_client.get(
        f"/citas/{test_cita.id}/visitas-potenciales/999/parte-trabajo"
    )
    assert response.status_code == 404
