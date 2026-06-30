"""orchestrator.py — Ponto de entrada do pipeline.

ESQUELETO (Fase 0). A orquestração completa — ingest → análise → impacto →
entrega, com logging, tratamento de erro por etapa e agendamento APScheduler —
é implementada na Fase 5. As funções abaixo são apenas marcadores de fluxo e
ainda não executam nada.
"""

# Pipeline (preenchido nas fases seguintes):
#   Fase 1: ingest.run()      -> List[Evento]
#   Fase 2: analysis.run()    -> List[Evento] classificados e rankeados
#   Fase 3: impact.run()      -> Briefing consolidado
#   Fase 4: delivery.run()    -> Telegram / DOCX / Sheets
#   Fase 5: scheduler + logging + tratamento de erro por etapa


def run_pipeline() -> None:
    """Executa o pipeline end-to-end. A implementar na Fase 5."""
    raise NotImplementedError("Pipeline implementado na Fase 5.")


if __name__ == "__main__":
    run_pipeline()
