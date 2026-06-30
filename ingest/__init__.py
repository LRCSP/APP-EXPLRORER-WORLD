"""ingest/ — Camada de Ingestão (Fase 1).

Busca e normaliza eventos das fontes do config/sources.yaml para o schema
comum Evento {titulo, fonte, url, data, setor, texto_bruto}. Inclui
deduplicação e tratamento de fonte fora do ar.
"""
from ingest.schema import Evento
from ingest.rss import run, fetch_source, deduplicate, FetchResult

__all__ = ["Evento", "run", "fetch_source", "deduplicate", "FetchResult"]
