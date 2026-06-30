"""Modelos consolidados: EventoBriefing e Briefing (fonte única de verdade).

O objeto Briefing é o que TODOS os adaptadores de entrega (Fase 4) consomem.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class EventoBriefing:
    """Um evento já analisado e com impacto operacional gerado."""
    titulo: str
    fonte: str
    url: str
    data: str
    setor: str
    geografia: str
    severidade: int          # 1-5
    relevancia: int          # 1-10
    impacto_custo: str
    impacto_cadeia: str
    exposicao_cyber: str
    acao_recomendada: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Briefing:
    """Consolidação única de tudo. Renderizado para Telegram, DOCX e Sheets."""
    gerado_em: str
    eventos: list[EventoBriefing] = field(default_factory=list)
    titulo: str = "Briefing de Inteligência Geopolítica Operacional"
    modo: str = "demo"        # "api" ou "demo"
    total_ingerido: int = 0   # nº de eventos brutos antes do Top N

    @classmethod
    def novo(cls, **kwargs) -> "Briefing":
        return cls(gerado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"), **kwargs)

    @property
    def por_setor(self) -> dict[str, list[EventoBriefing]]:
        agrupado: dict[str, list[EventoBriefing]] = {}
        for ev in self.eventos:
            agrupado.setdefault(ev.setor, []).append(ev)
        return agrupado

    def to_dict(self) -> dict[str, Any]:
        return {
            "titulo": self.titulo,
            "gerado_em": self.gerado_em,
            "modo": self.modo,
            "total_ingerido": self.total_ingerido,
            "eventos": [e.to_dict() for e in self.eventos],
        }
