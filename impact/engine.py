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
from config.editorias import rotulo
from ingest.schema import Evento
from impact.models import Briefing, EventoBriefing
from analysis.validators import validate_impact_block, clamp_severidade, clamp_relevancia

log = logging.getLogger("impact")

SYSTEM_PROMPT = (
    "Você é um analista de IA que traduz eventos de economia, mercado, política, "
    "comércio exterior, energia e tecnologia em impacto e cenário para pequenos "
    "negócios, MEIs, PMEs e investidores no Brasil. Tom direto, analítico, sem "
    "retórica vazia. Cada campo tem 1-2 frases acionáveis. "
    "REGRAS OBRIGATÓRIAS: nunca recomende comprar ou vender ativos específicos "
    "(não use 'compre' nem 'venda'); projeção é cenário PROVÁVEL, não garantia "
    "(não prometa previsão perfeita); não faça valuation nem due diligence. "
    "Responda APENAS com JSON válido."
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

# Setores adicionais (Tecnologia & Inovação, Economia, Geopolítica) — DEMO.
_DEMO["pt"].update({
    "tecnologia": {
        "impacto_custo": "Nova tecnologia/IA pode mudar custo de operação e produtividade; avalie adoção.",
        "impacto_cadeia": "Fornecedores de software/hardware podem alterar prazos e dependências.",
        "exposicao_cyber": "Toda nova adoção amplia a superfície de ataque; revise segurança.",
        "acao_recomendada": "Acompanhe a tendência e teste um piloto antes de comprometer orçamento.",
    },
    "economia": {
        "impacto_custo": "Juros, câmbio e inflação afetam diretamente custo de capital e insumos.",
        "impacto_cadeia": "Condições macro alteram crédito e prazos ao longo da cadeia.",
        "exposicao_cyber": "Sem exposição cyber direta relevante.",
        "acao_recomendada": "Revise premissas de câmbio e juros no orçamento do trimestre.",
    },
    "geopolitica": {
        "impacto_custo": "Tensão geopolítica pode elevar prêmios de risco, energia e frete.",
        "impacto_cadeia": "Conflitos e sanções reconfiguram rotas e fornecedores.",
        "exposicao_cyber": "Cenários de tensão elevam risco de ataques a infraestrutura.",
        "acao_recomendada": "Mapeie exposição a regiões em tensão e planos de contingência.",
    },
})
_DEMO["en"].update({
    "tecnologia": {
        "impacto_custo": "New tech/AI can shift operating cost and productivity; assess adoption.",
        "impacto_cadeia": "Software/hardware suppliers may change lead times and dependencies.",
        "exposicao_cyber": "Every new adoption widens the attack surface; review security.",
        "acao_recomendada": "Track the trend and pilot before committing budget.",
    },
    "economia": {
        "impacto_custo": "Rates, FX and inflation directly hit cost of capital and inputs.",
        "impacto_cadeia": "Macro conditions change credit and lead times across the chain.",
        "exposicao_cyber": "No material direct cyber exposure.",
        "acao_recomendada": "Revisit FX and rate assumptions in the quarter's budget.",
    },
    "geopolitica": {
        "impacto_custo": "Geopolitical tension can raise risk premia, energy and freight.",
        "impacto_cadeia": "Conflicts and sanctions reshape routes and suppliers.",
        "exposicao_cyber": "Tension scenarios raise the risk of infrastructure attacks.",
        "acao_recomendada": "Map exposure to tense regions and contingency plans.",
    },
})

_PREFIXO = {
    "pt": {"alto": "ALTO — ", "med": "Moderado — ", "baixo": "Baixo — ", "origem": "origem"},
    "en": {"alto": "HIGH — ", "med": "Moderate — ", "baixo": "Low — ", "origem": "source"},
}


def _bloco_demo(ev: Evento, lang: str) -> dict:
    setores = _DEMO.get(lang, _DEMO["pt"])
    setor = ev.extra.get("setor", ev.setor)
    base = dict(setores.get(setor, setores["exportacoes"]))
    sev = ev.extra.get("severidade", 1)
    geo = ev.extra.get("geografia", "Global")
    pf = _PREFIXO.get(lang, _PREFIXO["pt"])
    nivel = pf["alto"] if sev >= 4 else (pf["med"] if sev >= 2 else pf["baixo"])
    base["impacto_custo"] = f"{nivel}{base['impacto_custo']} ({pf['origem']}: {geo})"
    # DEMO não traduz de verdade: usa título/resumo originais.
    base["titulo"] = ev.extra.get("titulo_i18n", {}).get(lang) or ev.titulo
    base["resumo"] = (ev.texto_bruto or ev.titulo)[:400]
    base["projecao"] = ("Cenário provável nos próximos dias, a depender da evolução do tema."
                        if lang == "pt" else
                        "Likely scenario in the coming days, depending on how the topic evolves.")
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


def _blocos_api(brain, ev: Evento, idiomas: list[str], lente: dict | None = None) -> dict[str, dict]:
    """Retorna {idioma: {titulo, resumo, +4 campos de impacto}}. Uma só chamada."""
    lente_txt = ""
    if lente:
        lente_txt = (
            "\nPerspectiva do leitor (adapte impacto e ação a ela; a mesma para todos os idiomas): "
            f"PT: {lente.get('pt', '')} EN: {lente.get('en', '')}\n"
        )
    prompt = (
        f"Evento (idioma original da fonte: {ev.idioma_original}):\n"
        f"- Título original: {ev.titulo}\n"
        f"- Setor: {ev.extra.get('setor', ev.setor)}\n"
        f"- Geografia: {ev.extra.get('geografia', 'Global')} · país da fonte: {ev.pais or 'n/d'}\n"
        f"- Severidade (1-5): {ev.extra.get('severidade', 1)}\n"
        f"- Resumo original: {ev.texto_bruto[:600]}\n\n"
        "Para CADA idioma de "
        f"{idiomas} (pt=português, en=inglês), devolva um objeto com:\n"
        '  "titulo": tradução CONTEXTUAL (não literal) do título;\n'
        '  "resumo": 1-2 frases adaptando o resumo, explicando termos locais quando '
        'necessário (ex.: "Selic" em inglês -> "Selic, Brazil\'s benchmark interest rate");\n'
        '  "projecao": cenário PROVÁVEL nos próximos dias/semanas (não é garantia);\n'
        '  "impacto_custo", "impacto_cadeia", "exposicao_cyber", "acao_recomendada".\n'
        "Se a fonte estiver em outro idioma, traduza/adapte mantendo o sentido. "
        f"{lente_txt}"
        "Responda APENAS com JSON no formato:\n"
        '{"<idioma>": {"titulo":"...","resumo":"...","projecao":"...","impacto_custo":"...",'
        '"impacto_cadeia":"...","exposicao_cyber":"...","acao_recomendada":"..."}}'
    )
    texto = brain.complete(SYSTEM_PROMPT, prompt, max_tokens=1200, json=True)
    dados = _extrai_json(texto)
    out: dict[str, dict] = {}
    for lang in idiomas:
        d = dados.get(lang, {}) if isinstance(dados, dict) else {}
        bruto = {**{c: d.get(c) for c in CAMPOS}, "titulo": d.get("titulo"),
                 "resumo": d.get("resumo"), "projecao": d.get("projecao")}
        limpo, faltando = validate_impact_block(bruto)
        if faltando:
            log.warning("impacto[%s] campos ausentes: %s", lang, faltando)
        out[lang] = limpo
    return out


def montar_briefings(
    eventos_rankeados: list[Evento],
    settings: Settings | None = None,
    top_n: int | None = None,
    total_ingerido: int | None = None,
    lente: dict | None = None,
    titulos: dict | None = None,
) -> dict[str, Briefing]:
    """Gera o impacto dos Top N e devolve {idioma: Briefing}.

    `lente` (opcional) adapta o impacto à ótica de um perfil; `titulos` define
    o título do briefing por idioma (ex.: nome do perfil).
    """
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
    if titulos:
        for lang in idiomas:
            if titulos.get(lang):
                briefings[lang].titulo = titulos[lang]

    for ev in top:
        # blocos por idioma
        if use_api:
            try:
                blocos = _blocos_api(brain, ev, idiomas, lente)
                # Precisa de impacto real em ao menos um idioma; senão, DEMO.
                if not any(b.get("impacto_custo") or b.get("acao_recomendada") for b in blocos.values()):
                    raise ValueError("resposta sem impacto")
            except Exception as e:
                log.warning("impacto API falhou para '%s' (%s); DEMO aplicado", ev.titulo[:40], e)
                blocos = {lang: _bloco_demo(ev, lang) for lang in idiomas}
        else:
            blocos = {lang: _bloco_demo(ev, lang) for lang in idiomas}

        titulo_i18n = ev.extra.get("titulo_i18n", {})
        setor = ev.extra.get("setor", ev.setor)
        for lang in idiomas:
            bloco = blocos.get(lang) or _bloco_demo(ev, lang)
            titulo = bloco.get("titulo") or titulo_i18n.get(lang) or ev.titulo
            resumo = bloco.get("resumo") or (ev.texto_bruto or "")[:400]
            briefings[lang].eventos.append(
                EventoBriefing(
                    titulo=titulo,
                    fonte=ev.fonte,
                    url=ev.url,
                    data=ev.data,
                    setor=setor,
                    geografia=ev.extra.get("geografia", "Global"),
                    severidade=clamp_severidade(ev.extra.get("severidade", 1)),
                    relevancia=clamp_relevancia(ev.extra.get("relevancia", 1)),
                    impacto_custo=bloco["impacto_custo"],
                    impacto_cadeia=bloco["impacto_cadeia"],
                    exposicao_cyber=bloco["exposicao_cyber"],
                    acao_recomendada=bloco["acao_recomendada"],
                    projecao=bloco.get("projecao", ""),
                    resumo=resumo,
                    idioma_original=ev.idioma_original,
                    titulo_original=ev.titulo,
                    resumo_original=(ev.texto_bruto or "")[:600],
                    pais=ev.pais,
                    regiao=ev.regiao,
                    editoria=rotulo(setor, lang),
                )
            )
    return briefings


def montar_briefing(eventos_rankeados, settings=None, top_n=None, total_ingerido=None) -> Briefing:
    """Compat: devolve o Briefing do primeiro idioma configurado."""
    settings = settings or Settings.from_env()
    briefings = montar_briefings(eventos_rankeados, settings, top_n, total_ingerido)
    primeiro = (settings.idiomas or ["pt"])[0]
    return briefings[primeiro]
