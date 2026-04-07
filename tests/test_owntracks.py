from datetime import datetime, timezone

from app.routers.owntracks import _STRIP

OWNTRACKS_PAYLOAD = {
    "_type": "location",
    "lat": 51.5074,
    "lon": -0.1278,
    "tst": 1712345678,
    "acc": 12,
    "alt": 30,
    "vel": 0,
    "batt": 85,
    "bs": 2,
    "tid": "jg",
    "t": "u",
    "m": 1,
    "conn": "w",
    "SSID": "MyNetwork",
    "inregions": ["home"],
    "topic": "owntracks/jg/phone",
    "_http": True,
}


def test_owntracks_location_stored(client, write_key):
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"X-Api-Key": write_key},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_owntracks_location_entry_fields(client, write_key, read_key):
    client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"X-Api-Key": write_key},
    )
    entries = client.get(
        "/api/v1/entries/",
        params={"type": "location"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1
    e = entries[0]
    assert e["type"] == "location"
    assert e["source"] == "owntracks"
    assert e["external_id"] == "jg:1712345678"
    assert datetime.fromisoformat(e["timestamp"]) == datetime(
        2024, 4, 5, 19, 34, 38, tzinfo=timezone.utc
    )
    assert e["data"]["lat"] == 51.5074
    assert e["data"]["lon"] == -0.1278
    assert not _STRIP & e["data"].keys()


def test_owntracks_deduplicates(client, write_key, read_key):
    for _ in range(3):
        client.post(
            "/api/v1/owntracks",
            json=OWNTRACKS_PAYLOAD,
            headers={"X-Api-Key": write_key},
        )
    entries = client.get(
        "/api/v1/entries/",
        params={"type": "location"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1


def test_owntracks_ignores_non_location_type(client, write_key, read_key):
    resp = client.post(
        "/api/v1/owntracks",
        json={"_type": "lwt", "tst": 1712345678},
        headers={"X-Api-Key": write_key},
    )
    assert resp.status_code == 200
    assert resp.json() == []
    entries = client.get(
        "/api/v1/entries/",
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 0


def test_owntracks_requires_auth(client):
    resp = client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD)
    assert resp.status_code == 401


def test_owntracks_location_missing_tid(client, write_key):
    payload = {k: v for k, v in OWNTRACKS_PAYLOAD.items() if k != "tid"}
    resp = client.post(
        "/api/v1/owntracks",
        json=payload,
        headers={"X-Api-Key": write_key},
    )
    assert resp.status_code == 422


def test_owntracks_location_missing_tst(client, write_key):
    payload = {k: v for k, v in OWNTRACKS_PAYLOAD.items() if k != "tst"}
    resp = client.post(
        "/api/v1/owntracks",
        json=payload,
        headers={"X-Api-Key": write_key},
    )
    assert resp.status_code == 422


def test_owntracks_missing_type_field(client, write_key):
    payload = {k: v for k, v in OWNTRACKS_PAYLOAD.items() if k != "_type"}
    resp = client.post(
        "/api/v1/owntracks",
        json=payload,
        headers={"X-Api-Key": write_key},
    )
    assert resp.status_code == 422
