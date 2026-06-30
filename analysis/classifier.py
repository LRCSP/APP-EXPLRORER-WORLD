"""Motor de Análise/Classificação (Fase 2).

Para cada evento, define: setor, geografia, severidade (1-5) e relevância (1-10).

Dois modos:
- REAL: usa a API Anthropic com prompt enxuto e saída JSON estrita (batch).
  Tratamento de erro de parse: se o JSON vier quebrado, cai para heurística
  naquele lote sem derrubar o pipeline.
- DEMO (offline): se não houver ANTHROPIC_API_KEY, usa uma heurística
  determinística por palavras-chave para permitir um dry-run completo.

Saída: a mesma lista de eventos, com `extra` enriquecido e RANKEADA por
relevância (desc).
"""
from __future__ import annotations

import json
import logging
import re

from config.loader import Settings
from ingest.schema import Evento

log = logging.getLogger("analysis")

SETORES = ["energia", "petroleo", "cyber", "fertilizantes", "alimentos", "insumos", "exportacoes"]

SYSTEM_PROMPT = (
    "Você é um analista de inteligência geopolítica para empresários. "
    "Classifique cada notícia com objetividade. Responda APENAS com JSON válido, "
    "sem texto antes ou depois."
)

# Pistas para a heurística de demonstração (offline) e geografia.
_ALTA_SEVERIDADE = [
    "war", "guerra", "attack", "ataque", "sanction", "sanção", "ban", "embargo",
    "ransomware", "breach", "vazamento", "shortage", "escassez", "shutdown",
    "explosion", "strike", "greve", "blockade", "bloqueio", "missile", "invasion",
    "cyberattack", "outage", "collapse", "crisis", "crise", "surge", "disrupt",
]
_MEDIA_SEVERIDADE = [
    "price", "preço", "tariff", "tarifa", "export", "import", "supply", "deal",
    "cut", "corte", "rise", "alta", "fall", "queda", "deficit", "vulnerability",
    "patch", "warning", "alerta", "regulation", "OPEC", "OPEP",
]
_PAISES = {
    "russia": "Rússia", "ukraine": "Ucrânia", "ucrânia": "Ucrânia", "china": "China",
    "iran": "Irã", "israel": "Israel", "gaza": "Oriente Médio", "saudi": "Arábia Saudita",
    "opec": "OPEP", "opep": "OPEP", "venezuela": "Venezuela", "brazil": "Brasil",
    "brasil": "Brasil", "india": "Índia", "europe": "Europa", "eu ": "União Europeia",
    "united states": "EUA", "u.s.": "EUA", "us ": "EUA", "taiwan": "Taiwan",
    "north korea": "Coreia do Norte", "turkey": "Turquia", "germany": "Alemanha",
    "argentina": "Argentina", "mexico": "México", "africa": "África",
}


# --------------------------- Heurística (DEMO/fallback) ---------------------------

def _heuristica(ev: Evento) -> dict:
    texto = f"{ev.titulo} {ev.texto_bruto}".lower()
    hits_alta = sum(1 for k in _ALTA_SEVERIDADE if k in texto)
    hits_media = sum(1 for k in _MEDIA_SEVERIDADE if k in texto)

    severidade = min(5, 1 + hits_alta * 2 + (1 if hits_media else 0))
    relevancia = min(10, 2 + hits_alta * 3 + hits_media)

    geografia = "Global"
    for chave, nome in _PAISES.items():
        if chave in texto:
            geografia = nome
            break

    return {
        "setor": ev.setor,
        "geografia": geografia,
        "severidade": int(severidade),
        "relevancia": int(relevancia),
        # Sem chave não há tradução real: mantém o original nos dois idiomas.
        "titulo_i18n": {"pt": ev.titulo, "en": ev.titulo},
        "_modo": "demo",
    }


# ------------------------------- Modo REAL (API) ---------------------------------

def _extrai_json(texto: str):
    """Extrai o primeiro array/obj JSON de um texto, tolerando cercas ```json."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.MULTILINE).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"(\[.*\]|\{.*\})", texto, flags=re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise


def _classifica_lote_api(brain, lote: list[Evento]) -> list[dict]:
    itens = [
        {"id": i, "titulo": ev.titulo, "setor_fonte": ev.setor, "resumo": ev.texto_bruto[:400]}
        for i, ev in enumerate(lote)
    ]
    prompt = (
        "Classifique cada item do array abaixo. Para cada um devolva um objeto com:\n"
        '  "id": int (o mesmo do item),\n'
        f'  "setor": um de {SETORES},\n'
        '  "geografia": país/região principal (string curta) ou "Global",\n'
        '  "severidade": inteiro 1-5 (impacto potencial),\n'
        '  "relevancia": inteiro 1-10 (relevância para um empresário),\n'
        '  "titulo_pt": o título traduzido para português,\n'
        '  "titulo_en": o título em inglês.\n'
        "Responda APENAS com um array JSON desses objetos, na mesma ordem.\n\n"
        f"ITENS:\n{json.dumps(itens, ensure_ascii=False)}"
    )
    texto = brain.complete(SYSTEM_PROMPT, prompt, max_tokens=2000, json=True)
    dados = _extrai_json(texto)
    if not isinstance(dados, list):
        raise ValueError("esperava um array JSON")
    return dados


def run(eventos: list[Evento], settings: Settings | None = None, batch_size: int = 12) -> list[Evento]:
    """Classifica e RANKEIA os eventos por relevância (desc).

    Enriququece `ev.extra` com {setor, geografia, severidade, relevancia}.
    """
    settings = settings or Settings.from_env()

    from brain import make_brain
    brain = make_brain(settings, fast=True)

    if brain is None:
        log.info("Classificação em modo DEMO (nenhum provedor de IA configurado).")
        for ev in eventos:
            ev.extra.update(_heuristica(ev))
    else:
        log.info("Classificação via '%s'.", brain.name)
        for inicio in range(0, len(eventos), batch_size):
            lote = eventos[inicio:inicio + batch_size]
            try:
                dados = _classifica_lote_api(brain, lote)
                por_id = {d.get("id"): d for d in dados if isinstance(d, dict)}
                for i, ev in enumerate(lote):
                    d = por_id.get(i, {})
                    ev.extra.update({
                        "setor": d.get("setor", ev.setor),
                        "geografia": d.get("geografia", "Global"),
                        "severidade": int(d.get("severidade", 1) or 1),
                        "relevancia": int(d.get("relevancia", 1) or 1),
                        "titulo_i18n": {
                            "pt": d.get("titulo_pt") or ev.titulo,
                            "en": d.get("titulo_en") or ev.titulo,
                        },
                        "_modo": "api",
                    })
            except Exception as e:  # erro de parse/rede -> heurística no lote
                log.warning("lote %d falhou na API (%s); heurística aplicada", inicio // batch_size, e)
                for ev in lote:
                    ev.extra.update(_heuristica(ev))

    eventos_ordenados = sorted(
        eventos, key=lambda e: (e.extra.get("relevancia", 0), e.extra.get("severidade", 0)), reverse=True
    )
    return eventos_ordenados
