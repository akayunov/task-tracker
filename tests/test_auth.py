from fastapi import status
from sqlalchemy import text

from tasktracker.db.session import get_engine, session_scope
from tasktracker.services.auth import AuthService
from tests.helpers import auth_headers, login_user, register_user


async def test_register_normalizes_email_and_name(client):
    created = await register_user(
        client,
        '  User@Example.com ',
        full_name='  Ada Lovelace  ',
    )
    tokens = await login_user(client, 'user@example.com')
    me = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {tokens["access_token"]}'},
    )

    assert created['email'] == 'user@example.com'
    assert created['full_name'] == 'Ada Lovelace'
    assert created['role'] == 'user'
    assert 'hashed_password' not in created
    assert me.status_code == status.HTTP_200_OK
    assert me.json()['id'] == created['id']


async def test_duplicate_email_is_conflict(client):
    await register_user(client, 'same@example.com')
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'same@example.com',
            'password': 'Password1',
            'full_name': 'Other',
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()['code'] == 'email_taken'


async def test_weak_password_does_not_echo_secret(client):
    secret = 'Zz1'
    response = await client.post(
        '/api/v1/auth/register',
        json={'email': 'weak@example.com', 'password': secret, 'full_name': 'Weak'},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()['code'] == 'validation_error'
    assert secret not in response.text


async def test_login_rejects_bad_password(client):
    await register_user(client, 'ada@example.com')
    response = await client.post(
        '/api/v1/auth/login',
        json={'email': 'ada@example.com', 'password': 'wrong-password'},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()['code'] == 'invalid_credentials'
    assert response.headers['www-authenticate'] == 'Bearer'


async def test_oauth_form_and_refresh_rotation(client):
    await register_user(client, 'form@example.com')
    issued = await client.post(
        '/api/v1/auth/token',
        data={'username': 'form@example.com', 'password': 'Password1'},
    )
    assert issued.status_code == status.HTTP_200_OK, issued.text
    body = issued.json()

    refreshed = await client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': body['refresh_token']},
    )
    assert refreshed.status_code == status.HTTP_200_OK, refreshed.text
    reused = await client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': body['refresh_token']},
    )

    assert reused.status_code == status.HTTP_401_UNAUTHORIZED
    assert reused.json()['code'] == 'invalid_refresh_token'
    me = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {refreshed.json()["access_token"]}'},
    )
    assert me.status_code == status.HTTP_200_OK


async def test_logout_revokes_refresh_token(client):
    await register_user(client, 'bye@example.com')
    tokens = await login_user(client, 'bye@example.com')
    logout = await client.post(
        '/api/v1/auth/logout',
        json={'refresh_token': tokens['refresh_token']},
    )
    reused = await client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': tokens['refresh_token']},
    )

    assert logout.status_code == status.HTTP_204_NO_CONTENT
    assert logout.content == b''
    assert reused.status_code == status.HTTP_401_UNAUTHORIZED


async def test_inactive_user_cannot_login(client):
    await register_user(client, 'off@example.com')
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE users SET is_active = false WHERE email = 'off@example.com'"),
        )
    response = await client.post(
        '/api/v1/auth/login',
        json={'email': 'off@example.com', 'password': 'Password1'},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()['code'] == 'invalid_credentials'


async def test_missing_token_is_unauthorized(client):
    response = await client.get('/api/v1/auth/me')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()['code'] == 'not_authenticated'


async def test_register_rejects_role_field(client):
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'role@example.com',
            'password': 'Password1',
            'full_name': 'Role',
            'role': 'admin',
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_bootstrap_admin_is_created_once(client):
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
        '/api/v1/auth/login',
        json={'email': 'admin@example.com', 'password': 'Otherpass1'},
    )
    me = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {first["access_token"]}'},
    )

    assert second.status_code == status.HTTP_401_UNAUTHORIZED
    assert me.json()['role'] == 'admin'


async def test_user_directory_hides_password(client):
    headers = await auth_headers(client, 'listed@example.com', full_name='Listed User')
    response = await client.get('/api/v1/users', headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body['total'] == 1
    assert 'hashed_password' not in response.text
    assert body['items'][0]['email'] == 'listed@example.com'
