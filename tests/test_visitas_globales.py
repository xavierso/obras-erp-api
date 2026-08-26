import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.obra import Obra
from app.models.usuario import Usuario

@pytest.fixture
async def obras_con_visitas(db_session: AsyncSession, test_user: Usuario, auth_client: AsyncClient):
    obra1 = Obra(codigo="O-GLOBAL-1", nombre="Obra Global 1", usuario_id=test_user.id)
    obra2 = Obra(codigo="O-GLOBAL-2", nombre="Obra Global 2", usuario_id=test_user.id)
    db_session.add_all([obra1, obra2])
    await db_session.commit()
    await db_session.refresh(obra1)
    await db_session.refresh(obra2)

    await auth_client.post(f"/obras/{obra1.id}/visitas", data={"descripcion": "Visita en Obra 1"})
    await auth_client.post(f"/obras/{obra2.id}/visitas", data={"descripcion": "Visita en Obra 2"})
    
    return obra1, obra2

@pytest.mark.asyncio
async def test_listar_todas_las_visitas(auth_client: AsyncClient, obras_con_visitas):
    response = await auth_client.get("/visitas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Debería haber al menos las 2 visitas creadas por la fixture
    assert len(data) >= 2

    nombres_obras = [v["obra_nombre"] for v in data]
    assert "Obra Global 1" in nombres_obras
    assert "Obra Global 2" in nombres_obras

    descripciones = [v["descripcion"] for v in data]
    assert "Visita en Obra 1" in descripciones
    assert "Visita en Obra 2" in descripciones
