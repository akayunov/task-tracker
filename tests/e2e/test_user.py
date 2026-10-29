"""E2E: пользователи."""

from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.e2e.resources.user import User

pytestmark = pytest.mark.e2e


def test_user_directory_hides_password():
    user = User(full_name='Listed User').create()
    user.list_users(search=user.email, expected_body={'total': 1})


def test_get_user_profile():
    user = User(full_name='Profile User').create()
    user.get()


def test_get_missing_user():
    actor = User().create()
    User(id=str(uuid4())).get(
        as_user=actor,
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'user_not_found'},
    )


def test_cannot_delete_other_user():
    owner = User().create()
    stranger = User().create()
    owner.delete(
        as_user=stranger,
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'user_delete_forbidden'},
    )


def test_user_can_delete_own_account():
    user = User().create()
    user.login()
    access_token = user._access_token

    user.delete()
    user.me(
        access_token=access_token,
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'not_authenticated'},
    )
    user.login(
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'invalid_credentials'},
    )
