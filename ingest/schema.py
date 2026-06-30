"""Schema comum de evento, partilhado por todas as fases."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Evento:
    """Evento normalizado vindo de uma fonte de ingestão.

    Campos da Fase 1: titulo, fonte, url, data, setor, texto_bruto.
    Campos enriquecidos nas fases seguintes ficam em `extra` (análise/impacto).
    """
    titulo: str
    fonte: str
    url: str
    data: str            # ISO 8601 quando possível; string original caso contrário
    setor: str
    texto_bruto: str
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def chave_dedup(self) -> str:
        """Chave de deduplicação: prioriza URL; cai para título normalizado."""
        base = (self.url or self.titulo or "").strip().lower()
        return hashlib.sha1(base.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
