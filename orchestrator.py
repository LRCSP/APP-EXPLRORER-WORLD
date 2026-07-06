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
from impact.engine import montar_briefings
from delivery import telegram, docx_writer, sheets

log = logging.getLogger("orchestrator")
OUT = Path("out")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)-18s %(message)s",
        datefmt="%H:%M:%S",
    )


def construir_briefings(settings: Settings):
    """Etapas 1-3: ingestão, análise e impacto. Retorna ({idioma: Briefing}, resultados)."""
    log.info("== Etapa 1/3: ingestão ==")
    eventos, resultados = ingest.run()
    ok = sum(1 for r in resultados if r.ok)
    log.info("Fontes OK: %d/%d · eventos únicos: %d", ok, len(resultados), len(eventos))

    log.info("== Etapa 2/3: análise/classificação ==")
    eventos_rankeados = analysis.run(eventos, settings)

    log.info("== Etapa 3/3: impacto operacional (Top %d) ==", settings.top_n_events)
    briefings = montar_briefings(
        eventos_rankeados, settings, top_n=settings.top_n_events, total_ingerido=len(eventos)
    )
    modo = next(iter(briefings.values())).modo if briefings else "demo"
    log.info("Briefings prontos: idiomas=%s (modo %s)", list(briefings), modo)
    return briefings, resultados


def entregar(briefing, settings: Settings, dry_run: bool, lang: str = "pt",
             nome_base: str = "briefing") -> dict[str, str]:
    """Etapa 4: entrega nos 3 canais (no idioma `lang`), com erro isolado por canal."""
    status: dict[str, str] = {}
    suf = f"_{lang}"
    prev_base = "telegram_preview" if nome_base == "briefing" else f"{nome_base}_telegram"

    # --- DOCX (sempre gerado em arquivo) ---
    try:
        caminho = docx_writer.write(briefing, OUT / f"{nome_base}{suf}.docx")
        status["docx"] = f"OK -> {caminho}"
    except Exception as e:
        log.exception("DOCX falhou")
        status["docx"] = f"ERRO: {e}"

    # --- Telegram ---
    try:
        if dry_run or not (settings.telegram_bot_token and settings.telegram_chat_id):
            msgs = telegram.render(briefing)
            preview = OUT / f"{prev_base}{suf}.txt"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_text("\n\n----- (nova mensagem) -----\n\n".join(msgs), encoding="utf-8")
            status["telegram"] = f"DRY-RUN -> {len(msgs)} msg(s) em {preview}"
        else:
            n = telegram.send(briefing, settings)
            status["telegram"] = f"OK -> {n} mensagem(ns) enviada(s)"
    except Exception as e:
        log.exception("Telegram falhou")
        status["telegram"] = f"ERRO: {e}"

    # --- Sheets / download ---
    try:
        if dry_run or not (settings.google_sa_json_path and settings.google_sheets_id):
            caminho = sheets.to_csv(briefing, OUT / f"{nome_base}{suf}.csv")
            status["sheets"] = f"DRY-RUN -> CSV em {caminho}"
        else:
            n = sheets.append(briefing, settings)
            status["sheets"] = f"OK -> {n} linha(s) adicionada(s)"
    except Exception as e:
        log.exception("Sheets falhou")
        status["sheets"] = f"ERRO: {e}"

    return status


def run_pipeline(dry_run: bool = False) -> dict[str, dict[str, str]]:
    settings = Settings.from_env()
    briefings, _ = construir_briefings(settings)
    log.info("== Etapa 4: entrega ==")
    todos: dict[str, dict[str, str]] = {}
    for lang, briefing in briefings.items():
        log.info("-- idioma: %s --", lang)
        status = entregar(briefing, settings, dry_run, lang)
        for canal, s in status.items():
            log.info("  [%s/%s] %s", lang, canal, s)
        todos[lang] = status
    return todos


def run_profiles(dry_run: bool = False) -> dict[str, dict]:
    """Gera um briefing por PERFIL fixo (config/profiles.yaml).

    Classifica os eventos UMA vez; para cada perfil reordena por foco e gera o
    impacto sob a ótica do perfil.
    """
    from config.loader import load_profiles
    from analysis.profiles import rank_for_profile

    settings = Settings.from_env()
    perfis = load_profiles()
    log.info("== Perfis: %s ==", [p.id for p in perfis])

    log.info("== Ingestão + classificação (uma vez) ==")
    eventos, resultados = ingest.run()
    ok = sum(1 for r in resultados if r.ok)
    log.info("Fontes OK: %d/%d · eventos únicos: %d", ok, len(resultados), len(eventos))
    rankeados = analysis.run(eventos, settings)

    todos: dict[str, dict] = {}
    for p in perfis:
        log.info("== Perfil: %s ==", p.id)
        sel = rank_for_profile(rankeados, p, settings.max_per_source, settings.max_per_sector)
        titulos = {lang: p.nome_de(lang) for lang in (settings.idiomas or ["pt"])}
        briefs = montar_briefings(
            sel, settings, settings.top_n_events, len(eventos), lente=p.lente, titulos=titulos
        )
        for lang, briefing in briefs.items():
            status = entregar(briefing, settings, dry_run, lang, nome_base=f"briefing_{p.id}")
            for canal, s in status.items():
                log.info("  [%s/%s/%s] %s", p.id, lang, canal, s)
        todos[p.id] = briefs
    return todos


def parse_windows(janelas: list[str]) -> list[tuple[int, int]]:
    """Converte ['08:15','13:00'] -> [(8,15),(13,0)], ignorando entradas inválidas."""
    out: list[tuple[int, int]] = []
    for w in janelas:
        try:
            hh, mm = str(w).split(":")
            h, m = int(hh), int(mm)
            if 0 <= h <= 23 and 0 <= m <= 59:
                out.append((h, m))
            else:
                log.warning("Janela fora de faixa ignorada: %r", w)
        except (ValueError, AttributeError):
            log.warning("Janela inválida ignorada: %r", w)
    return out


def agendar() -> None:
    """Agenda execuções recorrentes via APScheduler.

    Prioriza as janelas intraday (SCHEDULE_WINDOWS, ex. 08:15/13:00/17:30, seg-sex);
    se nenhuma janela válida existir, cai no SCHEDULE_CRON.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    settings = Settings.from_env()
    sched = BlockingScheduler(timezone=settings.timezone)
    janelas = parse_windows(settings.schedule_windows)

    if janelas:
        for h, m in janelas:
            trigger = CronTrigger(
                day_of_week="mon-fri", hour=h, minute=m, timezone=settings.timezone
            )
            sched.add_job(
                lambda: run_pipeline(dry_run=False), trigger, id=f"briefing_{h:02d}{m:02d}"
            )
        horarios = ", ".join(f"{h:02d}:{m:02d}" for h, m in janelas)
        log.info("Agendado intraday: %s (%s, seg-sex). Ctrl+C para sair.", horarios, settings.timezone)
    else:
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
    parser.add_argument("--profiles", action="store_true",
                        help="gera um briefing por perfil fixo (config/profiles.yaml)")
    args = parser.parse_args()

    _setup_logging(Settings.from_env().log_level)

    if args.schedule:
        agendar()
        return 0
    if args.profiles:
        run_profiles(dry_run=not args.once)
    else:
        run_pipeline(dry_run=not args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
