from uuid import uuid4

from fastapi import status

from tests.helpers import auth_headers, create_task, promote_to_admin


async def test_create_sets_author(client):
    headers = await auth_headers(client, 'author@example.com', full_name='Author')
    response = await client.post(
        '/api/v1/tasks',
        json={'title': '  Ship API  ', 'description': '  '},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body['title'] == 'Ship API'
    assert body['description'] is None
    assert body['status'] == 'todo'
    assert body['priority'] == 'medium'
    assert body['version'] == 1
    assert body['completed_at'] is None
    assert body['author']['email'] == 'author@example.com'
    assert body['comments_count'] == 0
    assert response.headers['location'] == f'/api/v1/tasks/{body["id"]}'


async def test_filter_page_and_search(client):
    headers = await auth_headers(client, 'author@example.com')
    await create_task(client, headers, title='100% done')
    await create_task(client, headers, title='Other', priority='high')
    first = await create_task(client, headers, title='Alpha')
    done = await client.post(
        f'/api/v1/tasks/{first["id"]}/complete',
        json={'version': first['version']},
        headers=headers,
    )
    assert done.status_code == status.HTTP_200_OK, done.text

    percent = await client.get('/api/v1/tasks', params={'search': '%'}, headers=headers)
    exact = await client.get('/api/v1/tasks', params={'search': '100%'}, headers=headers)
    by_status = await client.get(
        '/api/v1/tasks',
        params={'status': 'done', 'page_size': 1},
        headers=headers,
    )
    empty_page = await client.get('/api/v1/tasks', params={'page': 5}, headers=headers)

    assert percent.json()['total'] == 1
    assert percent.json()['items'][0]['title'] == '100% done'
    assert exact.json()['total'] == 1
    assert by_status.json()['total'] == 1
    assert by_status.json()['pages'] == 1
    assert by_status.json()['items'][0]['completed_at'] is not None
    assert empty_page.json()['items'] == []
    assert empty_page.json()['total'] == 3


async def test_assignee_completes_only(client):
    author_headers = await auth_headers(client, 'author@example.com')
    assignee_headers = await auth_headers(client, 'assignee@example.com', full_name='Assignee')
    directory = await client.get(
        '/api/v1/users',
        params={'search': 'assignee'},
        headers=author_headers,
    )
    assignee_id = directory.json()['items'][0]['id']
    task = await create_task(client, author_headers, assignee_id=assignee_id)

    forbidden = await client.patch(
        f'/api/v1/tasks/{task["id"]}',
        json={'version': task['version'], 'title': 'Hijacked'},
        headers=assignee_headers,
    )
    completed = await client.post(
        f'/api/v1/tasks/{task["id"]}/complete',
        json={'version': task['version']},
        headers=assignee_headers,
    )

    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden.json()['code'] == 'task_edit_forbidden'
    assert completed.status_code == status.HTTP_200_OK, completed.text
    assert completed.json()['status'] == 'done'
    assert completed.json()['version'] == 2


async def test_stranger_cannot_mutate(client):
    author_headers = await auth_headers(client, 'author@example.com')
    stranger_headers = await auth_headers(client, 'stranger@example.com')
    task = await create_task(client, author_headers)

    status_change = await client.patch(
        f'/api/v1/tasks/{task["id"]}',
        json={'version': task['version'], 'status': 'in_progress'},
        headers=stranger_headers,
    )
    deletion = await client.delete(f'/api/v1/tasks/{task["id"]}', headers=stranger_headers)

    assert status_change.status_code == status.HTTP_403_FORBIDDEN
    assert status_change.json()['code'] == 'task_status_forbidden'
    assert deletion.status_code == status.HTTP_403_FORBIDDEN
    assert deletion.json()['code'] == 'task_delete_forbidden'


async def test_version_conflict_and_noop_update(client):
    headers = await auth_headers(client, 'author@example.com')
    task = await create_task(client, headers, title='Same')
    noop = await client.patch(
        f'/api/v1/tasks/{task["id"]}',
        json={'version': task['version'], 'title': 'Same'},
        headers=headers,
    )
    conflict = await client.patch(
        f'/api/v1/tasks/{task["id"]}',
        json={'version': 99, 'title': 'Next'},
        headers=headers,
    )

    assert noop.status_code == status.HTTP_200_OK
    assert noop.json()['version'] == task['version']
    assert conflict.status_code == status.HTTP_409_CONFLICT
    assert conflict.json()['code'] == 'task_version_conflict'


async def test_reopen_and_unassign(client):
    headers = await auth_headers(client, 'author@example.com')
    assignee = await auth_headers(client, 'assignee@example.com')
    users = await client.get('/api/v1/users', params={'search': 'assignee@'}, headers=headers)
    task = await create_task(
        client,
        headers,
        assignee_id=users.json()['items'][0]['id'],
        priority='high',
    )
    completed = await client.post(
        f'/api/v1/tasks/{task["id"]}/complete',
        json={'version': task['version']},
        headers=headers,
    )
    again = await client.post(
        f'/api/v1/tasks/{task["id"]}/complete',
        json={'version': completed.json()['version']},
        headers=headers,
    )
    reopened = await client.post(
        f'/api/v1/tasks/{task["id"]}/reopen',
        json={'version': again.json()['version']},
        headers=assignee,
    )
    cleared = await client.patch(
        f'/api/v1/tasks/{task["id"]}',
        json={'version': reopened.json()['version'], 'assignee_id': None, 'due_date': None},
        headers=headers,
    )

    assert again.json()['version'] == completed.json()['version']
    assert reopened.status_code == status.HTTP_200_OK, reopened.text
    assert reopened.json()['status'] == 'todo'
    assert reopened.json()['completed_at'] is None
    assert cleared.json()['assignee'] is None


async def test_unknown_assignee_and_missing_task(client):
    headers = await auth_headers(client, 'author@example.com')
    missing_user = await client.post(
        '/api/v1/tasks',
        json={'title': 'Orphan', 'assignee_id': str(uuid4())},
        headers=headers,
    )
    missing_task = await client.get(f'/api/v1/tasks/{uuid4()}', headers=headers)

    assert missing_user.status_code == status.HTTP_404_NOT_FOUND
    assert missing_user.json()['code'] == 'assignee_not_found'
    assert missing_task.status_code == status.HTTP_404_NOT_FOUND
    assert missing_task.json()['code'] == 'task_not_found'


async def test_admin_deletes_foreign_task(client):
    admin_headers = await auth_headers(client, 'admin@example.com')
    author_headers = await auth_headers(client, 'author@example.com')
    await promote_to_admin('admin@example.com')
    task = await create_task(client, author_headers)
    response = await client.delete(f'/api/v1/tasks/{task["id"]}', headers=admin_headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


async def test_unauthenticated_create_is_rejected(client):
    response = await client.post('/api/v1/tasks', json={'title': 'Nope'})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
