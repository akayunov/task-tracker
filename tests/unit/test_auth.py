"""Интеграционные кейсы auth, которые нельзя проверить только по HTTP e2e."""

from fastapi import status

from tasktracker.db.session import session_scope
from tasktracker.services.auth import AuthService
from tests.unit.helpers import API_PREFIX, login_user


async def test_bootstrap_admin_is_created_once(client):
    """Bootstrap вызывается из сервиса, не из HTTP API."""
    async with session_scope() as session:
        await AuthService(session).bootstrap_admin_user(
            email='admin@example.com',
            password='Adminpass1',
            full_name='Administrator',
        )
    async with session_scope() as session:
        await AuthService(session).bootstrap_admin_user(
            email='admin@example.com',
            password='Otherpass1',
            full_name='Administrator',
        )

    first = await login_user(client, 'admin@example.com', 'Adminpass1')
    second = await client.post(
        f'{API_PREFIX}/auth/login',
        json={'email': 'admin@example.com', 'password': 'Otherpass1'},
    )
    me = await client.get(
        f'{API_PREFIX}/auth/me',
        headers={'Authorization': f'Bearer {first["access_token"]}'},
    )

    assert second.status_code == status.HTTP_401_UNAUTHORIZED
    assert me.json()['role'] == 'admin'
