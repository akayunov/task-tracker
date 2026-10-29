"""Интеграционные кейсы комментариев, которые нельзя проверить только по HTTP e2e."""

from fastapi import status

from tests.unit.helpers import API_PREFIX, auth_headers, create_task, promote_to_admin


async def test_admin_and_cascade_delete(client):
    """Удаление чужого комментария админом: роль выставляется только через SQL."""
    admin_headers = await auth_headers(client, 'admin@example.com')
    author_headers = await auth_headers(client, 'author@example.com')
    await promote_to_admin('admin@example.com')
    task = await create_task(client, author_headers)
    comment = await client.post(
        f'{API_PREFIX}/tasks/{task["id"]}/comments',
        json={'body': 'Please delete'},
        headers=author_headers,
    )
    assert comment.status_code == status.HTTP_201_CREATED, comment.text

    removed = await client.delete(
        f'{API_PREFIX}/tasks/{task["id"]}/comments/{comment.json()["id"]}',
        headers=admin_headers,
    )
    assert removed.status_code == status.HTTP_204_NO_CONTENT

    second = await client.post(
        f'{API_PREFIX}/tasks/{task["id"]}/comments',
        json={'body': 'Still here'},
        headers=author_headers,
    )
    assert second.status_code == status.HTTP_201_CREATED
    deleted_task = await client.delete(f'{API_PREFIX}/tasks/{task["id"]}', headers=author_headers)
    missing = await client.get(f'{API_PREFIX}/tasks/{task["id"]}/comments', headers=author_headers)

    assert deleted_task.status_code == status.HTTP_204_NO_CONTENT
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert missing.json()['code'] == 'task_not_found'
