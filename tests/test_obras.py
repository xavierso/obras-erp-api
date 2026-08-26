import pytest
from httpx import AsyncClient
from app.models.obra import EstadoObra

@pytest.mark.asyncio
async def test_crear_obra(auth_client: AsyncClient):
    response = await auth_client.post(
        "/obras",
        json={
            "nombre": "Obra de Prueba",
            "cliente": "Cliente S.A.",
            "direccion": "Calle Falsa 123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Obra de Prueba"
    assert data["cliente"] == "Cliente S.A."
    assert "codigo" in data
    assert data["estado"] == EstadoObra.PENDIENTE
    return data["id"]

@pytest.mark.asyncio
async def test_listar_obras(auth_client: AsyncClient):
    # Crear una obra primero
    await auth_client.post(
        "/obras",
        json={"nombre": "Obra 1"}
    )
    
    response = await auth_client.get("/obras")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["nombre"] == "Obra 1"

@pytest.mark.asyncio
async def test_consultar_obra(auth_client: AsyncClient):
    # Crear una obra
    create_res = await auth_client.post("/obras", json={"nombre": "Obra 2"})
    obra_id = create_res.json()["id"]

    # Consultar la obra
    response = await auth_client.get(f"/obras/{obra_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == obra_id
    assert data["nombre"] == "Obra 2"

@pytest.mark.asyncio
async def test_cambiar_estado_obra(auth_client: AsyncClient):
    # Crear una obra
    create_res = await auth_client.post("/obras", json={"nombre": "Obra 3"})
    obra_id = create_res.json()["id"]

    # Cambiar estado
    response = await auth_client.patch(
        f"/obras/{obra_id}/estado",
        json={"estado": EstadoObra.EN_EJECUCION}
    )
    assert response.status_code == 200
    assert response.json()["estado"] == EstadoObra.EN_EJECUCION

@pytest.mark.asyncio
async def test_actualizar_detalle_obra(auth_client: AsyncClient):
    # Crear una obra
    create_res = await auth_client.post("/obras", json={"nombre": "Obra 4"})
    obra_id = create_res.json()["id"]

    # Actualizar detalle
    response = await auth_client.patch(
        f"/obras/{obra_id}",
        json={
            "nombre": "Obra 4 Modificada",
            "superficie_m2": 150.5,
            "progreso_porcentaje": 45
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Obra 4 Modificada"
    assert data["superficie_m2"] == 150.5
    assert data["progreso_porcentaje"] == 45
