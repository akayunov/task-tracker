from fastapi import status
from httpx import AsyncClient
from sqlalchemy import text

from tasktracker.core.config import get_settings
from tasktracker.db.session import get_engine

API_PREFIX = get_settings().api_prefix


async def register_user(
    client: AsyncClient,
    email: str,
    password: str = 'Password1',
    full_name: str = 'Test User',
) -> dict:
    response = await client.post(
        f'{API_PREFIX}/auth/register',
        json={'email': email, 'password': password, 'full_name': full_name},
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()


async def login_user(
    client: AsyncClient,
    email: str,
    password: str = 'Password1',
) -> dict:
    response = await client.post(
        f'{API_PREFIX}/auth/login',
        json={'email': email, 'password': password},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


async def auth_headers(
    client: AsyncClient,
    email: str,
    password: str = 'Password1',
    full_name: str = 'Test User',
) -> dict[str, str]:
    await register_user(client, email, password, full_name)
    tokens = await login_user(client, email, password)
    return {'Authorization': f'Bearer {tokens["access_token"]}'}


async def promote_to_admin(email: str) -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        result = await connection.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email"),
            {'email': email},
        )
    assert result.rowcount == 1


async def create_task(client: AsyncClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        'title': 'Write tests',
        'description': 'Cover the API',
        'priority': 'medium',
    }
    payload.update(overrides)
    response = await client.post(f'{API_PREFIX}/tasks', json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()
