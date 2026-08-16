from datetime import datetime as real_datetime

import pytest

import main


class StubResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        return self._json_data


class FixedDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2025, 1, 17, 8, 30, tzinfo=tz)


@pytest.mark.parametrize(
    ("status_code", "payload", "expected"),
    [
        (200, {"value": 42}, ({"value": 42}, None)),
        (401, {"message": "Invalid API key"}, (None, "Invalid API key")),
        (500, {}, (None, "Unknown error")),
    ],
    ids=["success", "api-error", "unknown-error"],
)
def test_fetch_data_handles_http_responses(monkeypatch, status_code, payload, expected):
    get_calls = []

    def fake_get(url, params):
        get_calls.append((url, params))
        return StubResponse(status_code=status_code, json_data=payload)

    monkeypatch.setattr(main.requests, "get", fake_get)

    result = main.fetch_data("https://example.test", {"city": "Yerevan"})

    assert result == expected
    assert get_calls == [("https://example.test", {"city": "Yerevan"})]


def test_fetch_data_returns_exception_text(monkeypatch):
    def fail_get(url, params):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(main.requests, "get", fail_get)

    assert main.fetch_data("https://example.test", {}) == (
        None,
        "network unavailable",
    )


def test_get_weather_formats_api_data(monkeypatch):
    monkeypatch.setattr(main, "CITY", "Yerevan")
    monkeypatch.setattr(main, "WEATHER_API_KEY", "api-key")
    monkeypatch.setattr(main, "UNITS", "metric")
    fetch_calls = []

    def fake_fetch(url, params):
        fetch_calls.append((url, params))
        return {"weather": [{"description": "clear sky"}], "main": {"temp": 18.5}}, None

    monkeypatch.setattr(main, "fetch_data", fake_fetch)

    result = main.get_weather()

    assert result == "Here in Yerevan Clear sky morning, gentle breeze blowing, 18.5°C"
    assert fetch_calls == [
        (
            "https://api.openweathermap.org/data/2.5/weather",
            {"q": "Yerevan", "appid": "api-key", "units": "metric"},
        )
    ]


def test_get_weather_reports_fetch_error(monkeypatch):
    monkeypatch.setattr(main, "fetch_data", lambda url, params: (None, "timeout"))

    assert main.get_weather() == "Error retrieving weather: timeout"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"weather": []},
        {"weather": [{"description": "rain"}]},
    ],
    ids=["missing-weather", "empty-weather", "missing-main"],
)
def test_get_weather_reports_incomplete_data(monkeypatch, payload):
    monkeypatch.setattr(main, "fetch_data", lambda url, params: (payload, None))

    assert main.get_weather().startswith("Incomplete weather data:")


def test_find_afternoon_forecast_returns_matching_entry():
    morning = {"dt_txt": "2025-01-17 12:00:00", "main": {"temp": 10}}
    afternoon = {"dt_txt": "2025-01-17 15:00:00", "main": {"temp": 12}}
    next_day = {"dt_txt": "2025-01-18 15:00:00", "main": {"temp": 13}}

    assert main.find_afternoon_forecast(
        [morning, afternoon, next_day], "2025-01-17"
    ) is afternoon
    assert (
        main.find_afternoon_forecast(
            [morning, afternoon, next_day], "2025-01-18", "12:00:00"
        )
        is None
    )


@pytest.mark.parametrize(
    ("data", "error", "expected"),
    [
        (None, "timeout", "Error retrieving forecast data: timeout"),
        ({}, None, "Error retrieving forecast data: No forecast list found"),
    ],
    ids=["fetch-error", "missing-list"],
)
def test_get_afternoon_forecast_reports_api_or_payload_error(
    monkeypatch, data, error, expected
):
    monkeypatch.setattr(main, "fetch_data", lambda url, params: (data, error))

    assert main.get_afternoon_forecast() == expected


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        (
            [{"dt_txt": "2025-01-17 15:00:00", "main": {"temp": 14}}],
            "This afternoon it will be going up to 14°C",
        ),
        (
            [{"dt_txt": "2025-01-18 15:00:00", "main": {"temp": 11.5}}],
            "This afternoon it will be going up to 11.5°C",
        ),
        ([], "Afternoon forecast not available."),
        (
            [{"dt_txt": "2025-01-17 15:00:00"}],
            "Afternoon forecast not available.",
        ),
    ],
    ids=["today", "tomorrow", "no-entries", "missing-main"],
)
def test_get_afternoon_forecast_selects_today_then_tomorrow(
    monkeypatch, entries, expected
):
    monkeypatch.setattr(main, "datetime", FixedDatetime)
    monkeypatch.setattr(main, "fetch_data", lambda url, params: ({"list": entries}, None))

    assert main.get_afternoon_forecast() == expected


def test_send_telegram_message_skips_request_without_token(monkeypatch, capsys):
    monkeypatch.setattr(main, "TELEGRAM_BOT_TOKEN", None)

    def unexpected_post(*args, **kwargs):
        pytest.fail("requests.post must not be called without a bot token")

    monkeypatch.setattr(main.requests, "post", unexpected_post)

    assert main.send_telegram_message("hello") is None
    assert capsys.readouterr().out == "TELEGRAM_BOT_TOKEN is not set!\n"


@pytest.mark.parametrize(
    ("response", "expected_output"),
    [
        (StubResponse(200), "Bot token loaded successfully.\nMessage sent successfully!\n"),
        (
            StubResponse(400, text="Bad Request"),
            "Bot token loaded successfully.\nError sending message: Bad Request\n",
        ),
    ],
    ids=["success", "api-error"],
)
def test_send_telegram_message_posts_payload(
    monkeypatch, capsys, response, expected_output
):
    monkeypatch.setattr(main, "TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setattr(main, "TELEGRAM_CHAT_ID", "12345")
    post_calls = []

    def fake_post(url, data):
        post_calls.append((url, data))
        return response

    monkeypatch.setattr(main.requests, "post", fake_post)

    main.send_telegram_message("hello")

    assert post_calls == [
        (
            "https://api.telegram.org/botsecret-token/sendMessage",
            {"chat_id": "12345", "text": "hello", "parse_mode": "HTML"},
        )
    ]
    assert capsys.readouterr().out == expected_output


def test_send_today_weather_sends_friday_sequence(monkeypatch):
    monkeypatch.setattr(main, "datetime", FixedDatetime)
    monkeypatch.setattr(main, "get_weather", lambda: "current weather")
    monkeypatch.setattr(main, "get_afternoon_forecast", lambda: "afternoon forecast")
    messages = []
    sleeps = []
    monkeypatch.setattr(main, "send_telegram_message", messages.append)
    monkeypatch.setattr(main.time, "sleep", sleeps.append)

    main.send_today_weather()

    assert messages == [
        "Good morning",
        "It's January 17, 2025\nand if YOU CAN BELIEVE IT - IT'S A FRIDAY ONCE AGAIN!!!",
        "current weather",
        "afternoon forecast",
        "And it looks like we're going to be enjoying beautiful blue skies and golden sunshine all along the way!",
        "Everyone, Have a great day!",
    ]
    assert sleeps == [3, 3, 3, 3, 4, 2]


def test_send_today_weather_uses_regular_weekday_message(monkeypatch):
    class MondayDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 20, 8, 30, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", MondayDatetime)
    monkeypatch.setattr(main, "get_weather", lambda: "weather")
    monkeypatch.setattr(main, "get_afternoon_forecast", lambda: "forecast")
    messages = []
    monkeypatch.setattr(main, "send_telegram_message", messages.append)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)

    main.send_today_weather()

    assert messages[1] == "It's January 20, 2025 and it's a Monday"


def test_send_today_number_sends_script_and_random_number(monkeypatch):
    monkeypatch.setattr(main, "datetime", FixedDatetime)
    monkeypatch.setattr(main.random, "randint", lambda start, end: 7)
    messages = []
    sleeps = []
    monkeypatch.setattr(main, "send_telegram_message", messages.append)
    monkeypatch.setattr(main.time, "sleep", sleeps.append)

    main.send_today_number()

    assert messages == [
        "Here we go for today's number!",
        "It's January 17, 2025",
        "Ten balls, each ball has a number",
        "Numbers one through ten",
        "Swirl the numbers",
        "Pick a number!",
        "Today's number is...",
        "7!",
    ]
    assert sleeps == [3, 3, 3, 3, 3, 3, 4, 2]
