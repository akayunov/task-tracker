"""E2E: регистрация, логин, токены."""

from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.e2e.resources.user import User

pytestmark = pytest.mark.e2e


def test_register_normalizes_email_and_name():
    user = User(
        email=f'  User-{uuid4().hex}@Example.com ',
        full_name='  Ada Lovelace  ',
    )
    user.create()
    user.login()
    user.me()


def test_duplicate_email_is_conflict():
    email = f'e2e-dup-{uuid4().hex}@example.com'
    User(email=email).create()
    User(email=email, full_name='Other').create(
        status_code=HTTPStatus.CONFLICT,
        expected_body={'code': 'email_taken'},
    )


def test_weak_password_does_not_echo_secret():
    User(password='Zz1', full_name='Weak').create(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        expected_body={'code': 'validation_error'},
    )


def test_login_rejects_bad_password():
    user = User().create()
    user.login(
        password='wrong-password',
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_headers={'www-authenticate': 'Bearer'},
        expected_body={'code': 'invalid_credentials'},
    )


def test_oauth_form_and_refresh_rotation():
    user = User().create()
    user.token()
    old_refresh = user._refresh_token

    user.refresh(token=old_refresh)
    user.refresh(
        token=old_refresh,
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'invalid_refresh_token'},
    )
    user.me()


def test_logout_revokes_refresh_token():
    user = User().create()
    user.login()
    old_refresh = user._refresh_token

    user.logout(token=old_refresh)
    user.refresh(
        token=old_refresh,
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'invalid_refresh_token'},
    )


def test_missing_token_is_unauthorized():
    User().me(
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'not_authenticated'},
    )


def test_register_rejects_role_field():
    User().create(role='admin', status_code=HTTPStatus.UNPROCESSABLE_ENTITY)


def test_login_unknown_email():
    User().login(
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'invalid_credentials'},
    )


def test_refresh_after_deactivate():
    user = User().create()
    user.login()
    old_refresh = user._refresh_token
    user.delete()
    user.refresh(
        token=old_refresh,
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'invalid_refresh_token'},
    )
