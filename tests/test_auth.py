def test_no_key_returns_401(client):
    # APIKeyHeader raises 401 when the header is absent
    response = client.get("/api/v1/entries")
    assert response.status_code == 401


def test_invalid_key_returns_401(client):
    response = client.get("/api/v1/entries", headers={"X-Api-Key": "not_a_valid_key"})
    assert response.status_code == 401


def test_read_key_cannot_write(client, read_key):
    payload = {"type": "test", "timestamp": "2026-01-01T00:00:00Z", "data": {}}
    response = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": read_key})
    assert response.status_code == 403


def test_write_key_cannot_read(client, write_key):
    response = client.get("/api/v1/entries", headers={"X-Api-Key": write_key})
    assert response.status_code == 403


def test_write_key_cannot_manage_keys(client, write_key):
    response = client.get("/api/v1/keys", headers={"X-Api-Key": write_key})
    assert response.status_code == 403


def test_admin_key_can_read(client, admin_key):
    response = client.get("/api/v1/entries", headers={"X-Api-Key": admin_key})
    assert response.status_code == 200


def test_admin_key_can_write(client, admin_key):
    payload = {"type": "test", "timestamp": "2026-01-01T00:00:00Z", "data": {}}
    response = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": admin_key})
    assert response.status_code == 201


def test_admin_key_can_manage_keys(client, admin_key):
    response = client.get("/api/v1/keys", headers={"X-Api-Key": admin_key})
    assert response.status_code == 200
