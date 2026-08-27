import pytest
from httpx import AsyncClient
from datetime import date

@pytest.mark.asyncio
async def test_obtener_calendario(auth_client: AsyncClient):
    # This will use the authenticated client
    response = await auth_client.get(f"/calendario/eventos?fecha_inicio={date.today().isoformat()}")
    print("STATUS", response.status_code)
    print("RESPONSE", response.json())
    assert response.status_code == 200
