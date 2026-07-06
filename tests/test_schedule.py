from config.loader import Settings
from orchestrator import parse_windows


def test_parse_windows_ok():
    assert parse_windows(["08:15", "13:00", "17:30"]) == [(8, 15), (13, 0), (17, 30)]


def test_parse_windows_ignora_invalidas():
    # formato ruim, hora fora de faixa e minuto fora de faixa são descartados
    assert parse_windows(["09:30", "banana", "25:00", "10:75", "7:5"]) == [(9, 30), (7, 5)]


def test_settings_default_windows():
    s = Settings()
    assert s.schedule_windows == ["08:15", "13:00", "17:30"]


def test_settings_windows_from_env(monkeypatch):
    monkeypatch.setenv("SCHEDULE_WINDOWS", "06:00, 12:00 ,18:00")
    s = Settings.from_env()
    assert s.schedule_windows == ["06:00", "12:00", "18:00"]


def test_settings_windows_env_vazio_usa_default(monkeypatch):
    monkeypatch.setenv("SCHEDULE_WINDOWS", "   ")
    s = Settings.from_env()
    assert s.schedule_windows == ["08:15", "13:00", "17:30"]
