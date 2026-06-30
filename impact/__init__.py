"""impact/ — Motor de Impacto Operacional (Fase 3, núcleo do produto).

Para os Top N eventos, gera o bloco de impacto para empresários:
{impacto_custo, impacto_cadeia, exposicao_cyber, acao_recomendada} e
consolida o objeto Briefing.
"""
from impact.models import Briefing, EventoBriefing
from impact.engine import montar_briefing, montar_briefings

__all__ = ["Briefing", "EventoBriefing", "montar_briefing", "montar_briefings"]
