import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone

@pytest.mark.asyncio
async def test_crear_cita(auth_client: AsyncClient):
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Reunión de prueba",
            "fecha_hora": future_date,
            "notas": "Notas de prueba",
            "recordatorio_minutos_antes": 30,
            "obra_id": None
        }
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["nombre_referencia"] == "Reunión de prueba"
    assert data["estado"] == "pendiente"
    assert "id" in data

@pytest.mark.asyncio
async def test_listar_citas(auth_client: AsyncClient):
    # Crear una cita primero
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_resp = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Cita a listar",
            "fecha_hora": future_date,
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    
    response = await auth_client.get("/citas")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c["nombre_referencia"] == "Cita a listar" for c in data)

@pytest.mark.asyncio
async def test_consultar_cita(auth_client: AsyncClient):
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_resp = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Cita a consultar",
            "fecha_hora": future_date,
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    cita_id = create_resp.json()["id"]

    response = await auth_client.get(f"/citas/{cita_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == cita_id
    assert data["nombre_referencia"] == "Cita a consultar"

@pytest.mark.asyncio
async def test_consultar_cita_no_encontrada(auth_client: AsyncClient):
    response = await auth_client.get("/citas/999999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_reprogramar_cita(auth_client: AsyncClient):
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_resp = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Cita original",
            "fecha_hora": future_date,
            "recordatorio_minutos_antes": 60
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    cita_id = create_resp.json()["id"]

    new_future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    response = await auth_client.patch(
        f"/citas/{cita_id}",
        json={
            "fecha_hora": new_future_date,
            "notas": "Nuevas notas",
            "recordatorio_minutos_antes": 120
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["notas"] == "Nuevas notas"
    assert data["recordatorio_minutos_antes"] == 120

@pytest.mark.asyncio
async def test_cambiar_estado_cita(auth_client: AsyncClient):
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_resp = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Cita para estado",
            "fecha_hora": future_date,
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    cita_id = create_resp.json()["id"]

    response = await auth_client.patch(
        f"/citas/{cita_id}/estado",
        json={
            "estado": "completada"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["estado"] == "completada"

@pytest.mark.asyncio
async def test_eliminar_cita(auth_client: AsyncClient):
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_resp = await auth_client.post(
        "/citas",
        json={
            "nombre_referencia": "Cita a eliminar",
            "fecha_hora": future_date,
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    cita_id = create_resp.json()["id"]

    delete_resp = await auth_client.delete(f"/citas/{cita_id}")
    assert delete_resp.status_code == 204

    get_resp = await auth_client.get(f"/citas/{cita_id}")
    assert get_resp.status_code == 404
