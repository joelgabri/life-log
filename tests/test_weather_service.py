from unittest.mock import MagicMock, patch

from app.services.weather import fetch_weather_entry, weather_external_id

OPEN_METEO_RESPONSE = {
    "current": {
        "temperature_2m": 14.5,
        "precipitation": 0.0,
        "wind_speed_10m": 12.3,
        "weather_code": 3,
    }
}


def _make_mock_response():
    mock = MagicMock()
    mock.json.return_value = OPEN_METEO_RESPONSE
    mock.raise_for_status.return_value = None
    return mock


def test_external_id_same_bucket():
    id1 = weather_external_id(51.5074, -0.1278, 1712345678)
    id2 = weather_external_id(51.5074, -0.1278, 1712345678 + 59)
    assert id1 == id2


def test_external_id_different_bucket():
    id1 = weather_external_id(51.5074, -0.1278, 1712344200)
    id2 = weather_external_id(51.5074, -0.1278, 1712344200 + 1800)
    assert id1 != id2


def test_external_id_different_location():
    id1 = weather_external_id(51.5074, -0.1278, 1712345678)
    id2 = weather_external_id(52.0000, -0.1278, 1712345678)
    assert id1 != id2


def test_external_id_rounds_to_2dp():
    # 51.5074 and 51.5099 both round to 51.51
    id1 = weather_external_id(51.5074, -0.1278, 1712345678)
    id2 = weather_external_id(51.5099, -0.1278, 1712345678)
    assert id1 == id2


def test_fetch_weather_entry_returns_entry():
    with patch("app.services.weather.httpx.get", return_value=_make_mock_response()):
        entry = fetch_weather_entry(51.5074, -0.1278, 1712345678)

    assert entry is not None
    assert entry.type == "weather"
    assert entry.source == "open-meteo"
    assert entry.data["temperature_2m"] == 14.5
    assert entry.data["weather_code"] == 3
    assert entry.data["lat"] == 51.5074
    assert entry.data["lon"] == -0.1278


def test_fetch_weather_entry_external_id_format():
    with patch("app.services.weather.httpx.get", return_value=_make_mock_response()):
        entry = fetch_weather_entry(51.5074, -0.1278, 1712345678)

    expected_bucket = (1712345678 // 1800) * 1800
    assert entry.external_id == f"weather:51.51:-0.13:{expected_bucket}"


def test_fetch_weather_entry_timestamp_is_bucket_start():
    with patch("app.services.weather.httpx.get", return_value=_make_mock_response()):
        entry = fetch_weather_entry(51.5074, -0.1278, 1712345678)

    expected_bucket = (1712345678 // 1800) * 1800
    assert entry.timestamp.timestamp() == expected_bucket


def test_fetch_weather_entry_returns_none_on_http_error():
    with patch("app.services.weather.httpx.get", side_effect=Exception("network error")):
        entry = fetch_weather_entry(51.5074, -0.1278, 1712345678)

    assert entry is None


def test_fetch_weather_entry_returns_none_on_bad_status():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("404")
    with patch("app.services.weather.httpx.get", return_value=mock):
        entry = fetch_weather_entry(51.5074, -0.1278, 1712345678)

    assert entry is None
