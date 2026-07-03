"""Adaptador de entrega: Google Sheets (gspread).

- rows(): converte o Briefing em linhas (1 evento por linha). Puro/testável.
- append(): autentica via service account e dá append na planilha.
- to_csv(): atalho local para inspecionar a saída sem credenciais.

Testável sozinho: rows() e to_csv() não tocam a rede.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from config.loader import Settings
from impact.models import Briefing

log = logging.getLogger("delivery.sheets")

CABECALHO = [
    "gerado_em", "editoria", "setor", "titulo", "resumo", "geografia",
    "pais", "severidade", "relevancia",
    "impacto_custo", "impacto_cadeia", "exposicao_cyber", "acao_recomendada",
    "fonte", "idioma_original", "titulo_original", "url", "data_evento",
]


def rows(briefing: Briefing) -> list[list[str]]:
    """Uma linha por evento, na ordem de CABECALHO (sem o cabeçalho em si)."""
    linhas: list[list[str]] = []
    for ev in briefing.eventos:
        linhas.append([
            briefing.gerado_em, getattr(ev, "editoria", "") or ev.setor, ev.setor,
            ev.titulo, getattr(ev, "resumo", ""), ev.geografia, getattr(ev, "pais", ""),
            str(ev.severidade), str(ev.relevancia),
            ev.impacto_custo, ev.impacto_cadeia, ev.exposicao_cyber, ev.acao_recomendada,
            ev.fonte, getattr(ev, "idioma_original", ""), getattr(ev, "titulo_original", "") or ev.titulo,
            ev.url, ev.data,
        ])
    return linhas


def to_csv(briefing: Briefing, path: str | Path = "out/briefing.csv") -> Path:
    """Escreve as mesmas linhas em CSV local (preview do que iria pro Sheets)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CABECALHO)
        w.writerows(rows(briefing))
    log.info("CSV (preview Sheets) gerado em %s", path)
    return path


def append(briefing: Briefing, settings: Settings | None = None) -> int:
    """Append das linhas na planilha configurada. Retorna nº de linhas inseridas."""
    settings = settings or Settings.from_env()
    if not settings.google_sa_json_path or not settings.google_sheets_id:
        raise RuntimeError(
            "GOOGLE_SA_JSON_PATH/GOOGLE_SHEETS_ID ausentes. Preencha o .env para enviar."
        )
    if not Path(settings.google_sa_json_path).exists():
        raise RuntimeError(f"Service account não encontrada: {settings.google_sa_json_path}")

    import gspread

    gc = gspread.service_account(filename=settings.google_sa_json_path)
    sh = gc.open_by_key(settings.google_sheets_id)
    try:
        ws = sh.worksheet(settings.google_sheets_worksheet)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=settings.google_sheets_worksheet, rows=1000, cols=len(CABECALHO))
        ws.append_row(CABECALHO)

    if not ws.get_all_values():  # planilha vazia -> grava cabeçalho
        ws.append_row(CABECALHO)

    linhas = rows(briefing)
    if linhas:
        ws.append_rows(linhas, value_input_option="RAW")
    log.info("Sheets: %d linhas adicionadas", len(linhas))
    return len(linhas)
