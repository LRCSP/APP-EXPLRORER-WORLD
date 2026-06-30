"""Carregamento de configuração: sources.yaml e variáveis de ambiente (.env).

Mantém toda a configuração FORA do código. Sem hardcode de chaves.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()  # carrega .env se existir; em produção usa env reais
except Exception:  # python-dotenv ausente não deve quebrar a config
    pass

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "config" / "sources.yaml"


@dataclass
class Source:
    name: str
    url: str
    sector: str
    type: str = "rss"
    enabled: bool = True


@dataclass
class SourcesConfig:
    sources: list[Source]
    timeout_seconds: int = 15
    user_agent: str = "GeoIntelMonitor/0.1"

    @property
    def enabled_sources(self) -> list[Source]:
        return [s for s in self.sources if s.enabled]


def load_sources(path: Path | str = SOURCES_PATH) -> SourcesConfig:
    """Lê o config/sources.yaml e devolve um SourcesConfig tipado."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {}) or {}
    raw_sources = data.get("sources", []) or []
    sources = [
        Source(
            name=s["name"],
            url=s["url"],
            sector=s.get("sector", "geral"),
            type=s.get("type", defaults.get("type", "rss")),
            enabled=s.get("enabled", True),
        )
        for s in raw_sources
    ]
    return SourcesConfig(
        sources=sources,
        timeout_seconds=int(defaults.get("timeout_seconds", 15)),
        user_agent=str(defaults.get("user_agent", "GeoIntelMonitor/0.1")),
    )


@dataclass
class Settings:
    """Configuração runtime vinda do ambiente (.env)."""
    # Provedor do "cérebro": "auto" (default), "gemini", "anthropic" ou "demo".
    llm_provider: str = "auto"
    # Gemini (faixa gratuita) — opção mais barata.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    # Anthropic (alternativa).
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"        # impacto (Fase 3)
    anthropic_model_fast: str = "claude-haiku-4-5"   # classificação/tradução (Fase 2)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    google_sa_json_path: str | None = None
    google_sheets_id: str | None = None
    google_sheets_worksheet: str = "Briefings"
    schedule_cron: str = "0 7 * * mon-fri"
    timezone: str = "America/Sao_Paulo"
    top_n_events: int = 10
    log_level: str = "INFO"
    idiomas: list[str] = field(default_factory=lambda: ["pt", "en"])

    @classmethod
    def from_env(cls) -> "Settings":
        idiomas = [i.strip().lower() for i in os.getenv("IDIOMAS", "pt,en").split(",") if i.strip()]
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            anthropic_model_fast=os.getenv("ANTHROPIC_MODEL_FAST", "claude-haiku-4-5"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            google_sa_json_path=os.getenv("GOOGLE_SA_JSON_PATH"),
            google_sheets_id=os.getenv("GOOGLE_SHEETS_ID"),
            google_sheets_worksheet=os.getenv("GOOGLE_SHEETS_WORKSHEET", "Briefings"),
            schedule_cron=os.getenv("SCHEDULE_CRON", "0 7 * * mon-fri"),
            timezone=os.getenv("TIMEZONE", "America/Sao_Paulo"),
            top_n_events=int(os.getenv("TOP_N_EVENTS", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            idiomas=idiomas or ["pt"],
        )
