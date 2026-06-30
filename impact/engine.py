"""Motor de Impacto Operacional (Fase 3) — núcleo do produto.

Para os Top N eventos rankeados, gera o bloco para empresários:
{impacto_custo, impacto_cadeia, exposicao_cyber, acao_recomendada}.

Modos:
- REAL: API Anthropic, um JSON por evento, tom analítico e direto.
- DEMO (offline): texto templated por setor/severidade, consistente, para
  permitir dry-run completo sem chave.

Saída: objeto Briefing consolidado.
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

# Frases-base por setor para o modo DEMO (substituídas pela API quando há chave).
_DEMO_SETOR = {
    "energia": {
        "impacto_custo": "Pressão sobre tarifas de energia e combustível; revise contratos de fornecimento e repasse.",
        "impacto_cadeia": "Possível atraso logístico em itens dependentes de transporte e energia intensiva.",
        "exposicao_cyber": "Infraestrutura energética é alvo recorrente; confirme segmentação de OT/TI.",
        "acao_recomendada": "Trave preço de energia/diesel onde possível e monitore o spread nas próximas semanas.",
    },
    "petroleo": {
        "impacto_custo": "Oscilação no barril afeta frete, plásticos e insumos derivados; custo de input pode subir.",
        "impacto_cadeia": "Volatilidade pode encarecer frete marítimo e prazos de importação.",
        "exposicao_cyber": "Risco indireto via fornecedores do setor; sem exposição direta imediata.",
        "acao_recomendada": "Reavalie hedge de combustível e antecipe compras sensíveis a preço de petróleo.",
    },
    "cyber": {
        "impacto_custo": "Incidente pode gerar custo de resposta, multa regulatória e parada operacional.",
        "impacto_cadeia": "Fornecedor comprometido pode interromper integrações e pedidos.",
        "exposicao_cyber": "Exposição DIRETA: verifique se a vulnerabilidade/ameaça citada afeta seus sistemas.",
        "acao_recomendada": "Aplique patches críticos, valide backups e revise acessos privilegiados hoje.",
    },
    "fertilizantes": {
        "impacto_custo": "Alta de fertilizantes eleva custo agrícola e, em cascata, preço de alimentos/insumos.",
        "impacto_cadeia": "Restrição de oferta (potássio/ureia) pode atrasar safra e contratos de fornecimento.",
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
        "impacto_cadeia": "Gargalo de mineração/insumo pode atrasar produção e reposição de estoque.",
        "exposicao_cyber": "Sem exposição cyber direta relevante.",
        "acao_recomendada": "Mapeie dependência de insumo crítico e qualifique fornecedor alternativo.",
    },
    "exportacoes": {
        "impacto_custo": "Sanções/tarifas alteram custo de importar e exportar; margem sob pressão.",
        "impacto_cadeia": "Controles de exportação podem bloquear insumos e travar pedidos internacionais.",
        "exposicao_cyber": "Sem exposição cyber direta relevante.",
        "acao_recomendada": "Revise exposição a mercados sancionados e ajuste rotas/fornecedores comerciais.",
    },
}


def _impacto_demo(ev: Evento) -> dict:
    base = _DEMO_SETOR.get(ev.setor, _DEMO_SETOR["exportacoes"])
    sev = ev.extra.get("severidade", 1)
    geo = ev.extra.get("geografia", "Global")
    prefixo = "ALTO — " if sev >= 4 else ("Moderado — " if sev >= 2 else "Baixo — ")
    out = dict(base)
    out["impacto_custo"] = f"{prefixo}{base['impacto_custo']} (origem: {geo})"
    return out


def _extrai_json(texto: str):
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _impacto_api(client, model: str, ev: Evento) -> dict:
    prompt = (
        "Evento:\n"
        f"- Título: {ev.titulo}\n"
        f"- Setor: {ev.extra.get('setor', ev.setor)}\n"
        f"- Geografia: {ev.extra.get('geografia', 'Global')}\n"
        f"- Severidade (1-5): {ev.extra.get('severidade', 1)}\n"
        f"- Resumo: {ev.texto_bruto[:600]}\n\n"
        "Gere o impacto operacional para um empresário. Responda APENAS com JSON:\n"
        '{"impacto_custo": "...", "impacto_cadeia": "...", '
        '"exposicao_cyber": "...", "acao_recomendada": "..."}'
    )
    msg = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    dados = _extrai_json(texto)
    return {c: str(dados.get(c, "")).strip() for c in CAMPOS}


def montar_briefing(
    eventos_rankeados: list[Evento],
    settings: Settings | None = None,
    top_n: int | None = None,
    total_ingerido: int | None = None,
) -> Briefing:
    """Gera o bloco de impacto dos Top N e consolida o objeto Briefing."""
    settings = settings or Settings.from_env()
    top_n = top_n or settings.top_n_events
    top = eventos_rankeados[:top_n]

    use_api = bool(settings.anthropic_api_key)
    client = None
    if use_api:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.anthropic_api_key)
        except Exception as e:
            log.warning("anthropic indisponível (%s); impacto em modo DEMO", e)
            use_api = False

    briefing = Briefing.novo(
        modo="api" if use_api else "demo",
        total_ingerido=total_ingerido if total_ingerido is not None else len(eventos_rankeados),
    )

    for ev in top:
        if use_api:
            try:
                bloco = _impacto_api(client, settings.anthropic_model, ev)
                if not any(bloco.values()):
                    bloco = _impacto_demo(ev)
            except Exception as e:
                log.warning("impacto API falhou para '%s' (%s); DEMO aplicado", ev.titulo[:40], e)
                bloco = _impacto_demo(ev)
        else:
            bloco = _impacto_demo(ev)

        briefing.eventos.append(
            EventoBriefing(
                titulo=ev.titulo,
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
    return briefing
