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
    # Metadados globais/bilíngues
    language: str = "en"        # idioma original da fonte (pt, en, es, ...)
    region: str = "global"      # global, americas, europe, asia, brazil, ...
    country: str = ""           # ISO-2 (US, BR, GB, ...) ou "" / "INT"
    tier: str = "media"         # official, media, aggregator
    max_entries: int = 0        # 0 = usa o default do SourcesConfig


@dataclass
class SourcesConfig:
    sources: list[Source]
    timeout_seconds: int = 15
    user_agent: str = "GeoIntelMonitor/0.1"
    default_max_entries: int = 40   # teto de itens por fonte (evita explosão)
    max_age_days: int = 0           # 0 = desligado; >0 descarta itens mais antigos

    @property
    def enabled_sources(self) -> list[Source]:
        return [s for s in self.sources if s.enabled]

    def limite(self, source: Source) -> int:
        return source.max_entries if source.max_entries > 0 else self.default_max_entries


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
            language=s.get("language", defaults.get("language", "en")),
            region=s.get("region", defaults.get("region", "global")),
            country=s.get("country", defaults.get("country", "")),
            tier=s.get("tier", defaults.get("tier", "media")),
            max_entries=int(s.get("max_entries", 0)),
        )
        for s in raw_sources
    ]
    env_cap = os.getenv("MAX_ENTRIES_PER_SOURCE")
    default_max = int(env_cap) if env_cap else int(defaults.get("max_entries", 40))
    return SourcesConfig(
        sources=sources,
        default_max_entries=default_max,
        max_age_days=int(os.getenv("MAX_AGE_DAYS", defaults.get("max_age_days", 0))),
        timeout_seconds=int(defaults.get("timeout_seconds", 15)),
        user_agent=str(defaults.get("user_agent", "GeoIntelMonitor/0.1")),
    )


PROFILES_PATH = ROOT / "config" / "profiles.yaml"


@dataclass
class Profile:
    """Perfil fixo de briefing (MVP)."""
    id: str
    nome: dict           # {pt, en}
    descricao: dict      # {pt, en}
    setores_foco: list[str]
    lente: dict          # {pt, en}

    def nome_de(self, lang: str) -> str:
        return self.nome.get(lang, self.nome.get("pt", self.id))


def load_profiles(path: Path | str = PROFILES_PATH) -> list[Profile]:
    """Lê config/profiles.yaml e devolve os perfis tipados."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [
        Profile(
            id=p["id"],
            nome=p.get("nome", {}),
            descricao=p.get("descricao", {}),
            setores_foco=list(p.get("setores_foco", [])),
            lente=p.get("lente", {}),
        )
        for p in data.get("profiles", [])
    ]


@dataclass
class Settings:
    """Configuração runtime vinda do ambiente (.env)."""
    # Provedor do "cérebro": "auto" (default), "gemini", "anthropic" ou "demo".
    llm_provider: str = "auto"
    # Gemini (faixa gratuita) — opção mais barata.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    # OpenRouter — um endpoint para testar muitas IAs.
    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/auto"
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
    # Quantos eventos (pré-filtrados de graça) vão para a IA classificar.
    ai_max_events: int = 50
    # Diversidade do ranking: máximo de eventos por fonte e por setor no topo.
    max_per_source: int = 2
    max_per_sector: int = 3
    log_level: str = "INFO"
    idiomas: list[str] = field(default_factory=lambda: ["pt", "en"])

    @classmethod
    def from_env(cls) -> "Settings":
        idiomas = [i.strip().lower() for i in os.getenv("IDIOMAS", "pt,en").split(",") if i.strip()]
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
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
            ai_max_events=int(os.getenv("AI_MAX_EVENTS", "50")),
            max_per_source=int(os.getenv("MAX_PER_SOURCE", "2")),
            max_per_sector=int(os.getenv("MAX_PER_SECTOR", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            idiomas=idiomas or ["pt"],
        )
