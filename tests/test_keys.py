def test_create_key_returns_raw_key(client, admin_key):
    payload = {"name": "my-collector", "scopes": ["write:entries"]}
    response = client.post("/api/v1/keys", json=payload, headers={"X-Api-Key": admin_key})
    assert response.status_code == 201
    body = response.json()
    assert "key" in body
    assert body["key"].startswith("ll_")
    assert body["name"] == "my-collector"
    assert body["scopes"] == ["write:entries"]


def test_list_keys(client, admin_key):
    client.post(
        "/api/v1/keys",
        json={"name": "key-one", "scopes": ["read:entries"]},
        headers={"X-Api-Key": admin_key},
    )
    client.post(
        "/api/v1/keys",
        json={"name": "key-two", "scopes": ["write:entries"]},
        headers={"X-Api-Key": admin_key},
    )
    response = client.get("/api/v1/keys", headers={"X-Api-Key": admin_key})
    assert response.status_code == 200
    names = [k["name"] for k in response.json()]
    assert "key-one" in names
    assert "key-two" in names


def test_list_keys_does_not_expose_raw_key(client, admin_key):
    response = client.get("/api/v1/keys", headers={"X-Api-Key": admin_key})
    assert response.status_code == 200
    for key in response.json():
        assert "key" not in key


def test_delete_key(client, admin_key):
    created = client.post(
        "/api/v1/keys",
        json={"name": "to-delete", "scopes": ["read:entries"]},
        headers={"X-Api-Key": admin_key},
    ).json()
    raw_key = created["key"]
    key_id = created["id"]

    # key works before deletion
    assert client.get("/api/v1/entries", headers={"X-Api-Key": raw_key}).status_code == 200

    delete_resp = client.delete(f"/api/v1/keys/{key_id}", headers={"X-Api-Key": admin_key})
    assert delete_resp.status_code == 204

    # key no longer works after deletion
    assert client.get("/api/v1/entries", headers={"X-Api-Key": raw_key}).status_code == 401


def test_delete_unknown_key_returns_404(client, admin_key):
    response = client.delete(
        "/api/v1/keys/00000000-0000-0000-0000-000000000000",
        headers={"X-Api-Key": admin_key},
    )
    assert response.status_code == 404
