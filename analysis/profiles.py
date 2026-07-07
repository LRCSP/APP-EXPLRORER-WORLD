"""Ranking por perfil (Fase 2.6).

Recebe os eventos já classificados (setor, severidade, relevância) e reordena
para um perfil específico: dá bônus aos setores de foco do perfil e reaplica a
diversidade. Assim o mesmo pool vira um briefing diferente para cada perfil,
sem reclassificar (economiza IA).
"""
from __future__ import annotations

from config.loader import Profile
from analysis.diversity import diversify
from ingest.schema import Evento


def rank_for_profile(
    eventos: list[Evento],
    profile: Profile,
    max_por_fonte: int = 2,
    max_por_setor: int = 3,
    bonus_foco: int = 4,
) -> list[Evento]:
    """Reordena os eventos para o perfil e reaplica a diversidade."""
    foco = set(profile.setores_foco)

    def score(ev: Evento) -> tuple[int, int]:
        rel = int(ev.extra.get("relevancia", 0))
        setor = ev.extra.get("setor", ev.setor)
        rel_ajustada = rel + (bonus_foco if setor in foco else 0)
        return (rel_ajustada, int(ev.extra.get("severidade", 0)))

    ordenados = sorted(eventos, key=score, reverse=True)
    return diversify(ordenados, max_por_fonte, max_por_setor)
