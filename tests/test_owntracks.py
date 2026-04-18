import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

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


_OPEN_METEO_RESPONSE = {
    "current": {
        "temperature_2m": 14.5,
        "precipitation": 0.0,
        "wind_speed_10m": 12.3,
        "weather_code": 3,
    }
}


@pytest.fixture(autouse=True)
def _mock_weather_globally(monkeypatch):
    """Prevent real weather API calls in all owntracks tests."""
    m = MagicMock()
    m.json.return_value = _OPEN_METEO_RESPONSE
    m.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.weather.httpx.get", lambda *a, **kw: m)


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


def _basic(username: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()


def test_owntracks_basic_auth(client, write_key):
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"Authorization": _basic("user", write_key)},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_owntracks_basic_auth_empty_username(client, write_key):
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"Authorization": _basic("", write_key)},
    )
    assert resp.status_code == 200


def test_owntracks_basic_auth_key_only_no_colon(client, write_key):
    credentials = base64.b64encode(write_key.encode()).decode()
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"Authorization": f"Basic {credentials}"},
    )
    assert resp.status_code == 200


def test_owntracks_basic_auth_wrong_key(client):
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"Authorization": _basic("user", "wrong_key")},
    )
    assert resp.status_code == 401


def test_owntracks_basic_auth_malformed(client):
    resp = client.post(
        "/api/v1/owntracks",
        json=OWNTRACKS_PAYLOAD,
        headers={"Authorization": "Basic !!!not-valid-base64!!!"},
    )
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


def test_owntracks_creates_weather_entry(client, write_key, read_key):
    client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key})

    entries = client.get(
        "/api/v1/entries/",
        params={"type": "weather"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(entries) == 1
    e = entries[0]
    assert e["source"] == "open-meteo"
    assert e["data"]["temperature_2m"] == 14.5
    assert e["external_id"].startswith("weather:")


def test_owntracks_weather_deduplicates_same_bucket(client, write_key, read_key):
    payload2 = {**OWNTRACKS_PAYLOAD, "tst": OWNTRACKS_PAYLOAD["tst"] + 59}
    client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key})
    client.post("/api/v1/owntracks", json=payload2, headers={"X-Api-Key": write_key})

    weather = client.get(
        "/api/v1/entries/",
        params={"type": "weather"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(weather) == 1


def test_owntracks_weather_new_entry_for_new_bucket(client, write_key, read_key):
    payload2 = {**OWNTRACKS_PAYLOAD, "tst": OWNTRACKS_PAYLOAD["tst"] + 1800}
    client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key})
    client.post("/api/v1/owntracks", json=payload2, headers={"X-Api-Key": write_key})

    weather = client.get(
        "/api/v1/entries/",
        params={"type": "weather"},
        headers={"X-Api-Key": read_key},
    ).json()
    assert len(weather) == 2


def test_owntracks_duplicate_location_skips_weather_http_call(client, write_key, monkeypatch):
    call_count = 0

    def counting_get(*a, **kw):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.json.return_value = _OPEN_METEO_RESPONSE
        m.raise_for_status.return_value = None
        return m

    monkeypatch.setattr("app.services.weather.httpx.get", counting_get)

    # Send the same location payload twice (simulates OwnTracks reconnect resend)
    client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key})
    client.post("/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key})

    assert call_count == 1


def test_owntracks_location_stored_even_if_weather_fails(client, write_key, read_key, monkeypatch):
    monkeypatch.setattr(
        "app.services.weather.httpx.get",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("timeout")),
    )

    resp = client.post(
        "/api/v1/owntracks", json=OWNTRACKS_PAYLOAD, headers={"X-Api-Key": write_key}
    )
    assert resp.status_code == 200

    location = client.get(
        "/api/v1/entries/", params={"type": "location"}, headers={"X-Api-Key": read_key}
    ).json()
    assert len(location) == 1

    weather = client.get(
        "/api/v1/entries/", params={"type": "weather"}, headers={"X-Api-Key": read_key}
    ).json()
    assert len(weather) == 0
