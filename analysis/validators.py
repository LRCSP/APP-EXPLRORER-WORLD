"""Validação/saneamento de dados que vêm da IA e de fontes externas.

Regras rígidas e com fallback seguro — nada de confiar em resposta parcial da
LLM ou em número fora de escala. Usado por classificação, impacto e exportação.
"""
from __future__ import annotations

import logging

log = logging.getLogger("validators")

CAMPOS_IMPACTO = ["impacto_custo", "impacto_cadeia", "exposicao_cyber", "acao_recomendada"]


def clamp_int(valor, lo: int, hi: int, default: int) -> int:
    """Converte para inteiro e limita ao intervalo [lo, hi]. Fallback = default."""
    try:
        n = int(round(float(valor)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def clamp_severidade(valor) -> int:
    """Severidade sempre inteiro 1..5."""
    return clamp_int(valor, 1, 5, 1)


def clamp_relevancia(valor) -> int:
    """Relevância sempre inteiro 1..10."""
    return clamp_int(valor, 1, 10, 1)


def texto(valor, default: str = "") -> str:
    """String não-nula e sem espaços nas pontas; fallback = default."""
    if valor is None:
        return default
    s = str(valor).strip()
    return s or default


def safe_url(url) -> str:
    """Só aceita http:// e https://; qualquer outra coisa vira '#' (anti-injeção)."""
    s = texto(url)
    if s.lower().startswith(("http://", "https://")):
        return s
    return "#"


def validate_classification(d: dict, ev, setores: list[str]) -> tuple[dict, list[str]]:
    """Normaliza a saída da classificação de UM evento.

    Devolve (campos_seguros, avisos). Nunca levanta exceção.
    """
    avisos: list[str] = []
    d = d if isinstance(d, dict) else {}

    setor = texto(d.get("setor"), ev.setor)
    if setor not in setores:
        avisos.append(f"setor inválido '{setor}' -> {ev.setor}")
        setor = ev.setor if ev.setor in setores else setores[0]

    sev = clamp_severidade(d.get("severidade"))
    rel = clamp_relevancia(d.get("relevancia"))
    if d.get("severidade") not in (None, "") and clamp_int(d.get("severidade"), 1, 5, -1) == -1:
        avisos.append("severidade fora de escala; clamp aplicado")

    titulo_pt = texto(d.get("titulo_pt"), ev.titulo)
    titulo_en = texto(d.get("titulo_en"), ev.titulo)

    return (
        {
            "setor": setor,
            "geografia": texto(d.get("geografia"), "Global"),
            "severidade": sev,
            "relevancia": rel,
            "titulo_i18n": {"pt": titulo_pt, "en": titulo_en},
        },
        avisos,
    )


def validate_impact_block(bloco: dict) -> tuple[dict, list[str]]:
    """Garante título/resumo/4 campos de impacto. Devolve (bloco_limpo, faltando).

    Se todos os 4 campos de impacto estiverem vazios, `faltando` inclui
    'impacto:vazio' — o chamador deve cair para o modo DEMO.
    """
    bloco = bloco if isinstance(bloco, dict) else {}
    limpo = {c: texto(bloco.get(c)) for c in CAMPOS_IMPACTO}
    limpo["titulo"] = texto(bloco.get("titulo"))
    limpo["resumo"] = texto(bloco.get("resumo"))

    faltando = [c for c in CAMPOS_IMPACTO if not limpo[c]]
    if len(faltando) == len(CAMPOS_IMPACTO):
        faltando.append("impacto:vazio")
    return limpo, faltando
