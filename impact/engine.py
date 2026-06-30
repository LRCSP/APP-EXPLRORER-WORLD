"""Motor de Impacto Operacional (Fase 3) — núcleo do produto.

Para os Top N eventos rankeados, gera o bloco para empresários:
{impacto_custo, impacto_cadeia, exposicao_cyber, acao_recomendada}.

Bilíngue: produz UM objeto Briefing por idioma configurado (Settings.idiomas).
Os adaptadores de entrega (Fase 4) NÃO precisam saber de idioma — recebem um
Briefing já no idioma certo. Isso mantém as "caixas" independentes.

Modos:
- REAL: API Anthropic, JSON com cada campo em pt e en, tom analítico e direto.
- DEMO (offline): textos templated por setor (pt e en), para dry-run sem chave.
"""
from __future__ import annotations

import json
import logging
import re

from config.loader import Settings
from ingest.schema import Evento
from impact.models import Briefing, EventoBriefing

log = logging.getLogger("impact")

SYSTEM_PROMPT = (
    "Você é um analista que traduz eventos geopolíticos em impacto operacional "
    "para donos de empresa. Tom direto, analítico, sem retórica vazia. "
    "Cada campo deve ter 1-2 frases acionáveis. Responda APENAS com JSON válido."
)

CAMPOS = ["impacto_custo", "impacto_cadeia", "exposicao_cyber", "acao_recomendada"]

# Frases-base por setor e idioma para o modo DEMO (substituídas pela API).
_DEMO = {
    "pt": {
        "energia": {
            "impacto_custo": "Pressão sobre tarifas de energia e combustível; revise contratos e repasse.",
            "impacto_cadeia": "Possível atraso logístico em itens dependentes de transporte e energia intensiva.",
            "exposicao_cyber": "Infraestrutura energética é alvo recorrente; confirme segmentação de OT/TI.",
            "acao_recomendada": "Trave preço de energia/diesel onde possível e monitore o spread nas próximas semanas.",
        },
        "petroleo": {
            "impacto_custo": "Oscilação no barril afeta frete, plásticos e insumos derivados; input pode subir.",
            "impacto_cadeia": "Volatilidade pode encarecer frete marítimo e prazos de importação.",
            "exposicao_cyber": "Risco indireto via fornecedores do setor; sem exposição direta imediata.",
            "acao_recomendada": "Reavalie hedge de combustível e antecipe compras sensíveis a preço de petróleo.",
        },
        "cyber": {
            "impacto_custo": "Incidente pode gerar custo de resposta, multa regulatória e parada operacional.",
            "impacto_cadeia": "Fornecedor comprometido pode interromper integrações e pedidos.",
            "exposicao_cyber": "Exposição DIRETA: verifique se a ameaça citada afeta seus sistemas.",
            "acao_recomendada": "Aplique patches críticos, valide backups e revise acessos privilegiados hoje.",
        },
        "fertilizantes": {
            "impacto_custo": "Alta de fertilizantes eleva custo agrícola e, em cascata, preço de alimentos.",
            "impacto_cadeia": "Restrição de oferta (potássio/ureia) pode atrasar safra e contratos.",
            "exposicao_cyber": "Sem exposição cyber direta relevante.",
            "acao_recomendada": "Garanta estoque/contratos de fertilizante antes de novas restrições de exportação.",
        },
        "alimentos": {
            "impacto_custo": "Choque de oferta de grãos pressiona custo de matéria-prima alimentar.",
            "impacto_cadeia": "Restrições de exportação podem reduzir disponibilidade e alongar prazos.",
            "exposicao_cyber": "Sem exposição cyber direta relevante.",
            "acao_recomendada": "Diversifique fornecedores de grãos e considere compra antecipada de itens críticos.",
        },
        "insumos": {
            "impacto_custo": "Preço de metais/minerais afeta custo de manufatura e reposição.",
            "impacto_cadeia": "Gargalo de mineração/insumo pode atrasar produção e estoque.",
            "exposicao_cyber": "Sem exposição cyber direta relevante.",
            "acao_recomendada": "Mapeie dependência de insumo crítico e qualifique fornecedor alternativo.",
        },
        "exportacoes": {
            "impacto_custo": "Sanções/tarifas alteram custo de importar e exportar; margem sob pressão.",
            "impacto_cadeia": "Controles de exportação podem bloquear insumos e travar pedidos.",
            "exposicao_cyber": "Sem exposição cyber direta relevante.",
            "acao_recomendada": "Revise exposição a mercados sancionados e ajuste rotas/fornecedores.",
        },
    },
    "en": {
        "energia": {
            "impacto_custo": "Upward pressure on energy and fuel costs; review supply contracts and pass-through.",
            "impacto_cadeia": "Possible logistics delays for transport- and energy-intensive items.",
            "exposicao_cyber": "Energy infrastructure is a frequent target; confirm OT/IT segmentation.",
            "acao_recomendada": "Lock energy/diesel prices where possible and watch the spread in coming weeks.",
        },
        "petroleo": {
            "impacto_custo": "Crude swings hit freight, plastics and derived inputs; input costs may rise.",
            "impacto_cadeia": "Volatility can raise ocean freight and lengthen import lead times.",
            "exposicao_cyber": "Indirect risk via sector suppliers; no immediate direct exposure.",
            "acao_recomendada": "Reassess fuel hedging and bring forward oil-price-sensitive purchases.",
        },
        "cyber": {
            "impacto_custo": "An incident can drive response cost, regulatory fines and downtime.",
            "impacto_cadeia": "A compromised supplier can disrupt integrations and orders.",
            "exposicao_cyber": "DIRECT exposure: check whether the cited threat affects your systems.",
            "acao_recomendada": "Apply critical patches, validate backups and review privileged access today.",
        },
        "fertilizantes": {
            "impacto_custo": "Higher fertilizer prices raise farm costs and, downstream, food prices.",
            "impacto_cadeia": "Supply curbs (potash/urea) can delay harvest and contracts.",
            "exposicao_cyber": "No material direct cyber exposure.",
            "acao_recomendada": "Secure fertilizer stock/contracts ahead of new export restrictions.",
        },
        "alimentos": {
            "impacto_custo": "A grain supply shock pressures food raw-material costs.",
            "impacto_cadeia": "Export curbs can cut availability and lengthen lead times.",
            "exposicao_cyber": "No material direct cyber exposure.",
            "acao_recomendada": "Diversify grain suppliers and consider forward-buying critical items.",
        },
        "insumos": {
            "impacto_custo": "Metal/mineral prices affect manufacturing and replacement costs.",
            "impacto_cadeia": "A mining/input bottleneck can delay production and inventory.",
            "exposicao_cyber": "No material direct cyber exposure.",
            "acao_recomendada": "Map critical-input dependence and qualify an alternative supplier.",
        },
        "exportacoes": {
            "impacto_custo": "Sanctions/tariffs change import and export costs; margins under pressure.",
            "impacto_cadeia": "Export controls can block inputs and stall orders.",
            "exposicao_cyber": "No material direct cyber exposure.",
            "acao_recomendada": "Review exposure to sanctioned markets and adjust routes/suppliers.",
        },
    },
}

_PREFIXO = {
    "pt": {"alto": "ALTO — ", "med": "Moderado — ", "baixo": "Baixo — ", "origem": "origem"},
    "en": {"alto": "HIGH — ", "med": "Moderate — ", "baixo": "Low — ", "origem": "source"},
}


def _bloco_demo(ev: Evento, lang: str) -> dict:
    setores = _DEMO.get(lang, _DEMO["pt"])
    base = dict(setores.get(ev.setor, setores["exportacoes"]))
    sev = ev.extra.get("severidade", 1)
    geo = ev.extra.get("geografia", "Global")
    pf = _PREFIXO.get(lang, _PREFIXO["pt"])
    nivel = pf["alto"] if sev >= 4 else (pf["med"] if sev >= 2 else pf["baixo"])
    base["impacto_custo"] = f"{nivel}{base['impacto_custo']} ({pf['origem']}: {geo})"
    return base


def _extrai_json(texto: str):
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _blocos_api(brain, ev: Evento, idiomas: list[str]) -> dict[str, dict]:
    """Retorna {idioma: {campo: texto}}. Pede todos os idiomas numa só chamada."""
    prompt = (
        "Evento:\n"
        f"- Título: {ev.titulo}\n"
        f"- Setor: {ev.extra.get('setor', ev.setor)}\n"
        f"- Geografia: {ev.extra.get('geografia', 'Global')}\n"
        f"- Severidade (1-5): {ev.extra.get('severidade', 1)}\n"
        f"- Resumo: {ev.texto_bruto[:600]}\n\n"
        "Gere o impacto operacional para um empresário, em CADA idioma de "
        f"{idiomas} (pt=português, en=inglês). Responda APENAS com JSON no formato:\n"
        '{"<idioma>": {"impacto_custo": "...", "impacto_cadeia": "...", '
        '"exposicao_cyber": "...", "acao_recomendada": "..."}}'
    )
    texto = brain.complete(SYSTEM_PROMPT, prompt, max_tokens=900, json=True)
    dados = _extrai_json(texto)
    out: dict[str, dict] = {}
    for lang in idiomas:
        d = dados.get(lang, {}) if isinstance(dados, dict) else {}
        out[lang] = {c: str(d.get(c, "")).strip() for c in CAMPOS}
    return out


def montar_briefings(
    eventos_rankeados: list[Evento],
    settings: Settings | None = None,
    top_n: int | None = None,
    total_ingerido: int | None = None,
) -> dict[str, Briefing]:
    """Gera o impacto dos Top N e devolve {idioma: Briefing}."""
    settings = settings or Settings.from_env()
    top_n = top_n or settings.top_n_events
    idiomas = settings.idiomas or ["pt"]
    top = eventos_rankeados[:top_n]

    from brain import make_brain
    brain = make_brain(settings, fast=False)
    use_api = brain is not None

    modo = brain.name if use_api else "demo"
    total = total_ingerido if total_ingerido is not None else len(eventos_rankeados)
    briefings = {lang: Briefing.novo(modo=modo, total_ingerido=total) for lang in idiomas}

    for ev in top:
        # blocos por idioma
        if use_api:
            try:
                blocos = _blocos_api(brain, ev, idiomas)
                if not any(any(b.values()) for b in blocos.values()):
                    raise ValueError("resposta vazia")
            except Exception as e:
                log.warning("impacto API falhou para '%s' (%s); DEMO aplicado", ev.titulo[:40], e)
                blocos = {lang: _bloco_demo(ev, lang) for lang in idiomas}
        else:
            blocos = {lang: _bloco_demo(ev, lang) for lang in idiomas}

        titulo_i18n = ev.extra.get("titulo_i18n", {})
        for lang in idiomas:
            bloco = blocos.get(lang) or _bloco_demo(ev, lang)
            briefings[lang].eventos.append(
                EventoBriefing(
                    titulo=titulo_i18n.get(lang, ev.titulo),
                    fonte=ev.fonte,
                    url=ev.url,
                    data=ev.data,
                    setor=ev.extra.get("setor", ev.setor),
                    geografia=ev.extra.get("geografia", "Global"),
                    severidade=int(ev.extra.get("severidade", 1)),
                    relevancia=int(ev.extra.get("relevancia", 1)),
                    impacto_custo=bloco["impacto_custo"],
                    impacto_cadeia=bloco["impacto_cadeia"],
                    exposicao_cyber=bloco["exposicao_cyber"],
                    acao_recomendada=bloco["acao_recomendada"],
                )
            )
    return briefings


def montar_briefing(eventos_rankeados, settings=None, top_n=None, total_ingerido=None) -> Briefing:
    """Compat: devolve o Briefing do primeiro idioma configurado."""
    settings = settings or Settings.from_env()
    briefings = montar_briefings(eventos_rankeados, settings, top_n, total_ingerido)
    primeiro = (settings.idiomas or ["pt"])[0]
    return briefings[primeiro]
