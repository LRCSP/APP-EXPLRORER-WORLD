"""Valida ao vivo cada fonte do config/sources.yaml e imprime um relatório.

Uso:
    python -m tools.validate_sources
"""
from __future__ import annotations

import logging

from config.loader import load_sources
from ingest.rss import fetch_source


def main() -> int:
    logging.basicConfig(level=logging.CRITICAL)
    cfg = load_sources()
    print(f"{'FONTE':40}{'SETOR':13}{'LÍNG':5}{'TIER':11}STATUS")
    print("-" * 90)
    ok = 0
    total_itens = 0
    for source in cfg.sources:
        meta = f"{source.language:5}{source.tier:11}"
        if not source.enabled:
            print(f"{source.name[:39]:40}{source.sector:13}{meta}(desativada)")
            continue
        r = fetch_source(source, cfg)
        if r.ok:
            ok += 1
            total_itens += r.n_entries
            print(f"{source.name[:39]:40}{source.sector:13}{meta}OK   {r.n_entries:>3} itens")
        else:
            print(f"{source.name[:39]:40}{source.sector:13}{meta}FALHA  {r.erro}")
    print("-" * 90)
    habilitadas = len(cfg.enabled_sources)
    print(f"Fontes OK: {ok}/{habilitadas}  |  Itens brutos coletados: {total_itens}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
