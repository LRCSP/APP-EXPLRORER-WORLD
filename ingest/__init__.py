"""ingest/ — Camada de Ingestão (Fase 1).

Busca e normaliza eventos das fontes do config/sources.yaml para o schema
comum: {titulo, fonte, url, data, setor, texto_bruto}. Inclui deduplicação
e tratamento de fonte fora do ar. Implementação na Fase 1.
"""
