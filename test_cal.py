import asyncio
from httpx import AsyncClient
from app.main import app

async def run():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # get token for a user
        login_data = {"username": "admin@empresa.com", "password": "password"} # or whatever
        # I'll just use a test db or existing db. The test db has users?
        pass

asyncio.run(run())
