from datetime import datetime, timezone

WAISTLINE_PAYLOAD = {
    "entry": {
        "dateTime": "2024-01-05T00:00:00.000Z",
        "items": [],
        "stats": {},
    },
    "nutrition": {
        "calories": 2350,
        "protein": 120,
        "carbs": 300,
        "fat": 80,
        "fiber": 25,
    },
    "entryDetails": [
        {"name": "Oatmeal", "calories": 300, "portion": 100},
    ],
}

_URL = "/waistline/api/v1/sync"


def test_waistline_sync_stored(client, write_key):
    resp = client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": write_key})
    assert resp.status_code == 200
    assert resp.json() == {"status": 200, "message": "Data synchronized."}


def test_waistline_sync_entry_fields(client, write_key, read_key):
    client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": write_key})

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "nutrition"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1
    e = entries[0]
    assert e["type"] == "nutrition"
    assert e["source"] == "waistline"
    assert e["external_id"] == "waistline:2024-01-05"
    assert datetime.fromisoformat(e["timestamp"]) == datetime(
        2024, 1, 5, 0, 0, 0, tzinfo=timezone.utc
    )
    assert e["data"]["nutrition"] == WAISTLINE_PAYLOAD["nutrition"]
    assert e["data"]["entryDetails"] == WAISTLINE_PAYLOAD["entryDetails"]


def test_waistline_deduplicates_same_day(client, write_key, read_key):
    for _ in range(3):
        client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": write_key})

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "nutrition"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1


def test_waistline_upsert_updates_nutrition(client, write_key, read_key):
    client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": write_key})

    updated = {
        **WAISTLINE_PAYLOAD,
        "nutrition": {**WAISTLINE_PAYLOAD["nutrition"], "calories": 9999},
    }
    client.post(_URL, json=updated, headers={"Authorization": write_key})

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "nutrition"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1
    assert entries[0]["data"]["nutrition"]["calories"] == 9999


def test_waistline_apikey_prefix_accepted(client, write_key):
    resp = client.post(
        _URL,
        json=WAISTLINE_PAYLOAD,
        headers={"Authorization": f"ApiKey {write_key}"},
    )
    assert resp.status_code == 200


def test_waistline_requires_auth(client):
    resp = client.post(_URL, json=WAISTLINE_PAYLOAD)
    assert resp.status_code == 401


def test_waistline_invalid_key_rejected(client):
    resp = client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": "ll_notavalidkey"})
    assert resp.status_code == 401


def test_waistline_apikey_prefix_invalid_key_rejected(client):
    resp = client.post(
        _URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": "ApiKey ll_notavalidkey"}
    )
    assert resp.status_code == 401


def test_waistline_wrong_scope_rejected(client, read_key):
    resp = client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": read_key})
    assert resp.status_code == 403


def test_waistline_missing_nutrition(client, write_key):
    payload = {k: v for k, v in WAISTLINE_PAYLOAD.items() if k != "nutrition"}
    resp = client.post(_URL, json=payload, headers={"Authorization": write_key})
    assert resp.status_code == 422


def test_waistline_missing_entry_datetime(client, write_key):
    payload = {**WAISTLINE_PAYLOAD, "entry": {"items": [], "stats": {}}}
    resp = client.post(_URL, json=payload, headers={"Authorization": write_key})
    assert resp.status_code == 422


def test_waistline_naive_datetime_rejected(client, write_key):
    payload = {**WAISTLINE_PAYLOAD, "entry": {"dateTime": "2024-01-05T00:00:00"}}
    resp = client.post(_URL, json=payload, headers={"Authorization": write_key})
    assert resp.status_code == 422


def test_waistline_entry_details_optional(client, write_key, read_key):
    payload = {k: v for k, v in WAISTLINE_PAYLOAD.items() if k != "entryDetails"}
    resp = client.post(_URL, json=payload, headers={"Authorization": write_key})
    assert resp.status_code == 200

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "nutrition"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1
    assert entries[0]["data"]["entryDetails"] == []


def test_waistline_different_days_both_stored(client, write_key, read_key):
    day2 = {
        **WAISTLINE_PAYLOAD,
        "entry": {**WAISTLINE_PAYLOAD["entry"], "dateTime": "2024-01-06T00:00:00.000Z"},
    }
    client.post(_URL, json=WAISTLINE_PAYLOAD, headers={"Authorization": write_key})
    client.post(_URL, json=day2, headers={"Authorization": write_key})

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "nutrition"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 2
    dates = {e["external_id"] for e in entries}
    assert dates == {"waistline:2024-01-05", "waistline:2024-01-06"}
