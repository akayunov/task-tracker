from fastapi import status


async def test_health_and_readiness(client):
    health = await client.get('/health')
    ready = await client.get('/ready')

    assert health.status_code == status.HTTP_200_OK
    assert health.json()['status'] == 'ok'
    assert ready.status_code == status.HTTP_200_OK
    assert ready.json()['status'] == 'ready'
    assert health.headers['x-request-id']


async def test_root_redirects_to_docs(client):
    response = await client.get('/')

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers['location'] == '/docs'
