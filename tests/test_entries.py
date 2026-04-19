BASE_ENTRY = {
    "type": "health_connect.steps",
    "source": "android_pixel_8",
    "timestamp": "2026-04-05T08:00:00Z",
    "data": {"count": 8432},
}


def test_create_entry(client, write_key):
    response = client.post("/api/v1/entries", json=BASE_ENTRY, headers={"X-Api-Key": write_key})
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "health_connect.steps"
    assert body["data"] == {"count": 8432}
    assert "id" in body
    assert body["updated_at"] is None


def test_create_entry_with_external_id(client, write_key):
    payload = {**BASE_ENTRY, "external_id": "hc_abc123"}
    response = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": write_key})
    assert response.status_code == 201
    body = response.json()
    assert body["external_id"] == "hc_abc123"
    assert body["updated_at"] is None


def test_resubmit_same_external_id_is_idempotent(client, write_key):
    payload = {**BASE_ENTRY, "external_id": "hc_idempotent"}
    r1 = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": write_key})
    r2 = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": write_key})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_update_existing_external_id(client, write_key):
    payload = {**BASE_ENTRY, "external_id": "hc_update_me"}
    r1 = client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": write_key})
    assert r1.json()["updated_at"] is None

    updated = {**payload, "data": {"count": 9999}}
    r2 = client.post("/api/v1/entries", json=updated, headers={"X-Api-Key": write_key})
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["data"] == {"count": 9999}
    assert r2.json()["updated_at"] is not None


def test_no_external_id_always_inserts(client, write_key):
    r1 = client.post("/api/v1/entries", json=BASE_ENTRY, headers={"X-Api-Key": write_key})
    r2 = client.post("/api/v1/entries", json=BASE_ENTRY, headers={"X-Api-Key": write_key})
    assert r1.json()["id"] != r2.json()["id"]


def test_batch_empty(client, write_key):
    response = client.post("/api/v1/entries/batch", json=[], headers={"X-Api-Key": write_key})
    assert response.status_code == 200
    assert response.json() == []


def test_batch_create(client, write_key):
    entries = [{**BASE_ENTRY, "external_id": f"hc_batch_{i}"} for i in range(3)]
    response = client.post("/api/v1/entries/batch", json=entries, headers={"X-Api-Key": write_key})
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_batch_upsert(client, write_key):
    # pre-insert one entry
    existing_payload = {**BASE_ENTRY, "external_id": "hc_existing_batch"}
    assert (
        client.post(
            "/api/v1/entries", json=existing_payload, headers={"X-Api-Key": write_key}
        ).status_code
        == 201
    )

    batch = [
        {**existing_payload, "data": {"count": 5000}},  # existing — should be updated
        {**BASE_ENTRY, "external_id": "hc_new_batch"},  # new
    ]
    response = client.post("/api/v1/entries/batch", json=batch, headers={"X-Api-Key": write_key})
    body = response.json()
    assert len(body) == 2
    existing = next(e for e in body if e["external_id"] == "hc_existing_batch")
    assert existing["data"] == {"count": 5000}
    assert existing["updated_at"] is not None


def test_batch_with_duplicate_external_ids_in_same_request(client, write_key):
    batch = [
        {**BASE_ENTRY, "external_id": "hc_dup", "data": {"count": 1}},
        {**BASE_ENTRY, "external_id": "hc_dup", "data": {"count": 2}},
    ]
    response = client.post("/api/v1/entries/batch", json=batch, headers={"X-Api-Key": write_key})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == body[1]["id"]
    assert body[0]["data"] == {"count": 2}
    assert body[1]["data"] == {"count": 2}


def test_batch_duplicate_in_request_and_in_db(client, write_key):
    payload = {**BASE_ENTRY, "external_id": "hc_db_and_batch_dup"}
    assert (
        client.post("/api/v1/entries", json=payload, headers={"X-Api-Key": write_key}).status_code
        == 201
    )

    batch = [
        {**payload, "data": {"count": 10}},
        {**payload, "data": {"count": 20}},
    ]
    response = client.post("/api/v1/entries/batch", json=batch, headers={"X-Api-Key": write_key})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == body[1]["id"]
    assert body[0]["data"] == {"count": 20}
    assert body[1]["data"] == {"count": 20}
    assert body[0]["updated_at"] is not None


def test_get_entries_returns_list(client, write_key, read_key):
    client.post("/api/v1/entries", json=BASE_ENTRY, headers={"X-Api-Key": write_key})
    response = client.get("/api/v1/entries", headers={"X-Api-Key": read_key})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_filter_by_type(client, write_key, read_key):
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "type": "type_a"},
        headers={"X-Api-Key": write_key},
    )
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "type": "type_b"},
        headers={"X-Api-Key": write_key},
    )
    response = client.get("/api/v1/entries?type=type_a", headers={"X-Api-Key": read_key})
    body = response.json()
    assert len(body) >= 1
    assert all(e["type"] == "type_a" for e in body)


def test_filter_by_time_range(client, write_key, read_key):
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "timestamp": "2026-01-01T00:00:00Z"},
        headers={"X-Api-Key": write_key},
    )
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "timestamp": "2026-06-01T00:00:00Z"},
        headers={"X-Api-Key": write_key},
    )
    response = client.get(
        "/api/v1/entries?start=2026-03-01T00:00:00Z&end=2026-12-31T00:00:00Z",
        headers={"X-Api-Key": read_key},
    )
    body = response.json()
    assert len(body) == 1
    assert "2026-06" in body[0]["timestamp"]


def test_filter_by_source(client, write_key, read_key):
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "source": "source_a"},
        headers={"X-Api-Key": write_key},
    )
    client.post(
        "/api/v1/entries",
        json={**BASE_ENTRY, "source": "source_b"},
        headers={"X-Api-Key": write_key},
    )
    response = client.get("/api/v1/entries?source=source_a", headers={"X-Api-Key": read_key})
    body = response.json()
    assert len(body) >= 1
    assert all(e["source"] == "source_a" for e in body)


def test_pagination(client, write_key, read_key):
    for _ in range(5):
        client.post("/api/v1/entries", json=BASE_ENTRY, headers={"X-Api-Key": write_key})

    page1 = client.get("/api/v1/entries?limit=3&offset=0", headers={"X-Api-Key": read_key}).json()
    page2 = client.get("/api/v1/entries?limit=3&offset=3", headers={"X-Api-Key": read_key}).json()
    assert len(page1) == 3
    assert len(page2) >= 2
    ids_p1 = {e["id"] for e in page1}
    ids_p2 = {e["id"] for e in page2}
    assert ids_p1.isdisjoint(ids_p2)
