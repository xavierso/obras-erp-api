import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.obra import Obra
from app.models.usuario import Usuario

@pytest.fixture
async def obra_test(db_session: AsyncSession, test_user: Usuario) -> Obra:
    obra = Obra(
        codigo="OBR-VISITAS",
        nombre="Obra para Visitas",
        usuario_id=test_user.id
    )
    db_session.add(obra)
    await db_session.commit()
    await db_session.refresh(obra)
    return obra

@pytest.mark.asyncio
async def test_registrar_visita_sin_archivos(auth_client: AsyncClient, obra_test: Obra):
    response = await auth_client.post(
        f"/obras/{obra_test.id}/visitas",
        data={"descripcion": "Visita inicial de prueba"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["descripcion"] == "Visita inicial de prueba"
    assert data["obra_id"] == obra_test.id
    assert len(data["archivos"]) == 0

@pytest.mark.asyncio
async def test_registrar_visita_obra_no_encontrada(auth_client: AsyncClient):
    response = await auth_client.post(
        "/obras/9999/visitas",
        data={"descripcion": "No existes"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Obra no encontrada"

@pytest.mark.asyncio
async def test_listar_visitas(auth_client: AsyncClient, obra_test: Obra):
    # Crear visita
    await auth_client.post(
        f"/obras/{obra_test.id}/visitas",
        data={"descripcion": "Visita 1"}
    )
    
    response = await auth_client.get(f"/obras/{obra_test.id}/visitas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["descripcion"] == "Visita 1"
    assert data[0]["obra_id"] == obra_test.id

@pytest.mark.asyncio
async def test_obtener_visita(auth_client: AsyncClient, obra_test: Obra):
    resp_crear = await auth_client.post(
        f"/obras/{obra_test.id}/visitas",
        data={"descripcion": "Visita Específica"}
    )
    visita_id = resp_crear.json()["id"]

    response = await auth_client.get(f"/obras/{obra_test.id}/visitas/{visita_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["descripcion"] == "Visita Específica"
    assert data["id"] == visita_id

@pytest.mark.asyncio
async def test_actualizar_visita(auth_client: AsyncClient, obra_test: Obra):
    resp_crear = await auth_client.post(
        f"/obras/{obra_test.id}/visitas",
        data={"descripcion": "Visita Original"}
    )
    visita_id = resp_crear.json()["id"]

    response = await auth_client.put(
        f"/obras/{obra_test.id}/visitas/{visita_id}",
        data={"descripcion": "Visita Actualizada"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["descripcion"] == "Visita Actualizada"
