from fastapi import status

from tests.helpers import auth_headers, create_task, promote_to_admin


async def test_comment_crud_and_permissions(client):
    author_headers = await auth_headers(client, 'author@example.com')
    other_headers = await auth_headers(client, 'other@example.com')
    task = await create_task(client, author_headers)
    created = await client.post(
        f'/api/v1/tasks/{task["id"]}/comments',
        json={'body': '  Looks good  '},
        headers=other_headers,
    )
    assert created.status_code == status.HTTP_201_CREATED, created.text
    comment = created.json()
    assert comment['body'] == 'Looks good'
    assert comment['version'] == 1

    forbidden = await client.patch(
        f'/api/v1/tasks/{task["id"]}/comments/{comment["id"]}',
        json={'version': 1, 'body': 'Changed'},
        headers=author_headers,
    )
    updated = await client.patch(
        f'/api/v1/tasks/{task["id"]}/comments/{comment["id"]}',
        json={'version': 1, 'body': 'Changed'},
        headers=other_headers,
    )
    conflict = await client.patch(
        f'/api/v1/tasks/{task["id"]}/comments/{comment["id"]}',
        json={'version': 1, 'body': 'Again'},
        headers=other_headers,
    )
    listed = await client.get(f'/api/v1/tasks/{task["id"]}/comments', headers=author_headers)

    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden.json()['code'] == 'comment_edit_forbidden'
    assert updated.status_code == status.HTTP_200_OK, updated.text
    assert updated.json()['version'] == 2
    assert conflict.status_code == status.HTTP_409_CONFLICT
    assert conflict.json()['code'] == 'comment_version_conflict'
    assert listed.json()['total'] == 1
    assert listed.json()['items'][0]['body'] == 'Changed'


async def test_admin_and_cascade_delete(client):
    admin_headers = await auth_headers(client, 'admin@example.com')
    author_headers = await auth_headers(client, 'author@example.com')
    await promote_to_admin('admin@example.com')
    task = await create_task(client, author_headers)
    comment = await client.post(
        f'/api/v1/tasks/{task["id"]}/comments',
        json={'body': 'Please delete'},
        headers=author_headers,
    )
    assert comment.status_code == status.HTTP_201_CREATED, comment.text

    removed = await client.delete(
        f'/api/v1/tasks/{task["id"]}/comments/{comment.json()["id"]}',
        headers=admin_headers,
    )
    assert removed.status_code == status.HTTP_204_NO_CONTENT

    second = await client.post(
        f'/api/v1/tasks/{task["id"]}/comments',
        json={'body': 'Still here'},
        headers=author_headers,
    )
    assert second.status_code == status.HTTP_201_CREATED
    deleted_task = await client.delete(f'/api/v1/tasks/{task["id"]}', headers=author_headers)
    missing = await client.get(f'/api/v1/tasks/{task["id"]}/comments', headers=author_headers)

    assert deleted_task.status_code == status.HTTP_204_NO_CONTENT
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert missing.json()['code'] == 'task_not_found'


async def test_comment_requires_existing_task(client):
    headers = await auth_headers(client, 'author@example.com')
    response = await client.post(
        '/api/v1/tasks/00000000-0000-0000-0000-000000000000/comments',
        json={'body': 'Nobody home'},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['code'] == 'task_not_found'
