"""Интеграционные кейсы задач, которые нельзя проверить только по HTTP e2e."""

from fastapi import status

from tests.unit.helpers import API_PREFIX, auth_headers, create_task, promote_to_admin


async def test_admin_deletes_foreign_task(client):
    """Повышение до admin только через SQL — публичного API смены роли нет."""
    admin_headers = await auth_headers(client, 'admin@example.com')
    author_headers = await auth_headers(client, 'author@example.com')
    await promote_to_admin('admin@example.com')
    task = await create_task(client, author_headers)
    response = await client.delete(f'{API_PREFIX}/tasks/{task["id"]}', headers=admin_headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
