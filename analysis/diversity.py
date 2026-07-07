"""Diversidade do ranking (Fase 2.5).

Um briefing pago não pode ter "10 notícias parecidas" — precisa de 10 sinais
diferentes e úteis. Este passo, aplicado sobre a lista já ordenada por
relevância, garante variedade:

- descarta quase-duplicatas (títulos muito parecidos);
- limita eventos por fonte e por setor no topo;
- mantém a prioridade de relevância (o que passar do limite vai para o fim).
"""
from __future__ import annotations

import re

from ingest.schema import Evento

_STOP = {"para", "com", "por", "que", "the", "and", "of", "in", "to", "a", "o", "os", "as", "de", "da", "do"}


def _tokens(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-zà-ú0-9]+", (texto or "").lower()) if len(w) > 3 and w not in _STOP}


def _similar(a: str, b: str, limiar: float = 0.55) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return inter / len(ta | tb) >= limiar


def _titulo(ev: Evento) -> str:
    return ev.extra.get("titulo_i18n", {}).get("pt") or ev.titulo


def diversify(eventos: list[Evento], max_por_fonte: int = 2, max_por_setor: int = 3) -> list[Evento]:
    """Reordena a lista (já ordenada por relevância) para maximizar variedade.

    O topo fica diverso; itens que estouram os limites vão para o fim; quase-
    duplicatas são removidas.
    """
    selecionados: list[Evento] = []
    overflow: list[Evento] = []
    titulos_sel: list[str] = []
    por_fonte: dict[str, int] = {}
    por_setor: dict[str, int] = {}

    for ev in eventos:
        titulo = _titulo(ev)
        if any(_similar(titulo, t) for t in titulos_sel):
            continue  # quase-duplicata: descarta
        fonte = ev.fonte
        setor = ev.extra.get("setor", ev.setor)
        if por_fonte.get(fonte, 0) >= max_por_fonte or por_setor.get(setor, 0) >= max_por_setor:
            overflow.append(ev)
            continue
        selecionados.append(ev)
        titulos_sel.append(titulo)
        por_fonte[fonte] = por_fonte.get(fonte, 0) + 1
        por_setor[setor] = por_setor.get(setor, 0) + 1

    return selecionados + overflow
