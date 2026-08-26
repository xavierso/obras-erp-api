import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_dashboard_resumen(auth_client: AsyncClient):
    mock_resumen = {
        "obras_activas": 5,
        "visitas_hoy": 2,
        "visitas_semana": 10,
        "documentos_nuevos_semana": 3
    }
    
    with patch("app.routers.dashboard.obtener_resumen_dashboard", return_value=mock_resumen):
        response = await auth_client.get("/dashboard/resumen")
        
        assert response.status_code == 200
        assert response.json() == mock_resumen

@pytest.mark.asyncio
async def test_dashboard_resumen_no_autorizado(async_client: AsyncClient):
    response = await async_client.get("/dashboard/resumen")
    assert response.status_code == 401
