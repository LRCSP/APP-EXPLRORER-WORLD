"""orchestrator.py — Pipeline end-to-end e agendamento (Fase 5).

Fluxo: ingest -> análise -> impacto -> entrega (Telegram, DOCX, Sheets).

Princípios:
- Tratamento de erro POR ETAPA: a falha de uma fonte ou de um canal de entrega
  não derruba o briefing inteiro.
- Logging claro de cada etapa.

Uso:
    python orchestrator.py --dry-run     # roda tudo, NÃO envia; gera arquivos em out/
    python orchestrator.py --once        # roda e entrega nos canais configurados
    python orchestrator.py --schedule    # agenda execuções (APScheduler / SCHEDULE_CRON)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from config.loader import Settings
import ingest
import analysis
from impact.engine import montar_briefing
from delivery import telegram, docx_writer, sheets

log = logging.getLogger("orchestrator")
OUT = Path("out")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)-18s %(message)s",
        datefmt="%H:%M:%S",
    )


def construir_briefing(settings: Settings):
    """Etapas 1-3: ingestão, análise e impacto. Retorna (briefing, resultados_fontes)."""
    log.info("== Etapa 1/3: ingestão ==")
    eventos, resultados = ingest.run()
    ok = sum(1 for r in resultados if r.ok)
    log.info("Fontes OK: %d/%d · eventos únicos: %d", ok, len(resultados), len(eventos))

    log.info("== Etapa 2/3: análise/classificação ==")
    eventos_rankeados = analysis.run(eventos, settings)

    log.info("== Etapa 3/3: impacto operacional (Top %d) ==", settings.top_n_events)
    briefing = montar_briefing(
        eventos_rankeados, settings, top_n=settings.top_n_events, total_ingerido=len(eventos)
    )
    log.info("Briefing pronto: %d eventos (modo %s)", len(briefing.eventos), briefing.modo)
    return briefing, resultados


def entregar(briefing, settings: Settings, dry_run: bool) -> dict[str, str]:
    """Etapa 4: entrega nos 3 canais, com erro isolado por canal."""
    status: dict[str, str] = {}

    # --- DOCX (sempre gerado em arquivo) ---
    try:
        caminho = docx_writer.write(briefing, OUT / "briefing.docx")
        status["docx"] = f"OK -> {caminho}"
    except Exception as e:
        log.exception("DOCX falhou")
        status["docx"] = f"ERRO: {e}"

    # --- Telegram ---
    try:
        if dry_run or not (settings.telegram_bot_token and settings.telegram_chat_id):
            msgs = telegram.render(briefing)
            preview = OUT / "telegram_preview.txt"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_text("\n\n----- (nova mensagem) -----\n\n".join(msgs), encoding="utf-8")
            status["telegram"] = f"DRY-RUN -> {len(msgs)} msg(s) em {preview}"
        else:
            n = telegram.send(briefing, settings)
            status["telegram"] = f"OK -> {n} mensagem(ns) enviada(s)"
    except Exception as e:
        log.exception("Telegram falhou")
        status["telegram"] = f"ERRO: {e}"

    # --- Sheets ---
    try:
        if dry_run or not (settings.google_sa_json_path and settings.google_sheets_id):
            caminho = sheets.to_csv(briefing, OUT / "briefing.csv")
            status["sheets"] = f"DRY-RUN -> CSV em {caminho}"
        else:
            n = sheets.append(briefing, settings)
            status["sheets"] = f"OK -> {n} linha(s) adicionada(s)"
    except Exception as e:
        log.exception("Sheets falhou")
        status["sheets"] = f"ERRO: {e}"

    return status


def run_pipeline(dry_run: bool = False) -> dict[str, str]:
    settings = Settings.from_env()
    briefing, _ = construir_briefing(settings)
    log.info("== Etapa 4: entrega ==")
    status = entregar(briefing, settings, dry_run)
    for canal, s in status.items():
        log.info("  [%s] %s", canal, s)
    return status


def agendar() -> None:
    """Agenda execuções recorrentes via APScheduler usando SCHEDULE_CRON."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    settings = Settings.from_env()
    sched = BlockingScheduler(timezone=settings.timezone)
    trigger = CronTrigger.from_crontab(settings.schedule_cron, timezone=settings.timezone)
    sched.add_job(lambda: run_pipeline(dry_run=False), trigger, id="briefing")
    log.info("Agendado: '%s' (%s). Ctrl+C para sair.", settings.schedule_cron, settings.timezone)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agendador encerrado.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor de Inteligência Geopolítica Operacional")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="roda tudo sem enviar; gera arquivos em out/")
    g.add_argument("--once", action="store_true", help="roda uma vez e entrega nos canais configurados")
    g.add_argument("--schedule", action="store_true", help="agenda execuções (APScheduler)")
    args = parser.parse_args()

    _setup_logging(Settings.from_env().log_level)

    if args.schedule:
        agendar()
        return 0
    run_pipeline(dry_run=not args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
