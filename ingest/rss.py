"""Ingestão de feeds RSS/Atom: busca, normaliza, deduplica e tolera falhas.

- Busca cada fonte com timeout e User-Agent configuráveis.
- Normaliza para o schema Evento {titulo, fonte, url, data, setor, texto_bruto}.
- Deduplica por URL (cai para título) dentro do lote.
- Uma fonte fora do ar NÃO derruba as demais: o erro é capturado e reportado.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime

import feedparser
import requests

from config.loader import Source, SourcesConfig, load_sources
from ingest.schema import Evento

log = logging.getLogger("ingest")

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _TAG_RE.sub("", text).strip()


def _parse_date(entry) -> str:
    """Devolve data ISO 8601 quando o feed fornece struct_time; senão string crua."""
    for attr in ("published_parsed", "updated_parsed"):
        st = getattr(entry, attr, None)
        if st:
            try:
                return datetime.fromtimestamp(mktime(st), tz=timezone.utc).isoformat()
            except Exception:
                pass
    return getattr(entry, "published", "") or getattr(entry, "updated", "") or ""


@dataclass
class FetchResult:
    source: Source
    ok: bool
    eventos: list[Evento]
    erro: str | None = None
    n_entries: int = 0
    status: int | None = None


def fetch_source(source: Source, cfg: SourcesConfig) -> FetchResult:
    """Busca e normaliza uma única fonte. Captura qualquer erro de rede/parse."""
    headers = {"User-Agent": cfg.user_agent}
    try:
        resp = requests.get(source.url, headers=headers, timeout=cfg.timeout_seconds)
        status = resp.status_code
        if status >= 400:
            return FetchResult(source, False, [], f"HTTP {status}", status=status)
        parsed = feedparser.parse(resp.content)
    except requests.RequestException as e:
        return FetchResult(source, False, [], f"rede: {e.__class__.__name__}: {e}")
    except Exception as e:  # parse ou inesperado
        return FetchResult(source, False, [], f"{e.__class__.__name__}: {e}")

    entries = getattr(parsed, "entries", []) or []
    if parsed.get("bozo") and not entries:
        return FetchResult(source, False, [], f"feed inválido: {parsed.get('bozo_exception')}", status=status)

    # Janela temporal opcional (descarta itens antigos com data conhecida).
    if cfg.max_age_days > 0:
        corte = datetime.now(tz=timezone.utc).timestamp() - cfg.max_age_days * 86400
        def _recente(e):
            st = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
            return (mktime(st) >= corte) if st else True  # sem data: mantém
        entries = [e for e in entries if _recente(e)]

    # Teto de itens por fonte (evita explosão — ex.: OpenAI News com 1000+).
    limite = cfg.limite(source)
    if limite > 0:
        entries = entries[:limite]

    eventos: list[Evento] = []
    for e in entries:
        titulo = _strip_html(getattr(e, "title", "")) or "(sem título)"
        resumo = _strip_html(getattr(e, "summary", "")) or _strip_html(getattr(e, "description", ""))
        eventos.append(
            Evento(
                titulo=titulo,
                fonte=source.name,
                url=getattr(e, "link", "") or "",
                data=_parse_date(e),
                setor=source.sector,
                texto_bruto=resumo or titulo,
                idioma_original=source.language,
                pais=source.country,
                regiao=source.region,
            )
        )
    return FetchResult(source, True, eventos, None, n_entries=len(entries), status=status)


def deduplicate(eventos: list[Evento]) -> list[Evento]:
    """Remove duplicatas por chave (URL -> título). Mantém a primeira ocorrência."""
    vistos: set[str] = set()
    unicos: list[Evento] = []
    for ev in eventos:
        if ev.chave_dedup in vistos:
            continue
        vistos.add(ev.chave_dedup)
        unicos.append(ev)
    return unicos


def run(cfg: SourcesConfig | None = None) -> tuple[list[Evento], list[FetchResult]]:
    """Ingere todas as fontes habilitadas.

    Retorna (eventos_deduplicados, resultados_por_fonte). Os resultados servem
    para reportar quais fontes responderam e quais falharam.
    """
    cfg = cfg or load_sources()
    resultados: list[FetchResult] = []
    todos: list[Evento] = []
    for source in cfg.enabled_sources:
        r = fetch_source(source, cfg)
        resultados.append(r)
        if r.ok:
            todos.extend(r.eventos)
            log.info("OK   %-45s %d itens", source.name, r.n_entries)
        else:
            log.warning("FALHA %-44s %s", source.name, r.erro)
    return deduplicate(todos), resultados
