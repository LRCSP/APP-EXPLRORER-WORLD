"""analysis/ — Motor de Análise/Classificação (Fase 2).

Para cada evento: setor, geografia, severidade (1-5) e relevância (1-10)
via API Anthropic (JSON estrito), com fallback heurístico (modo DEMO).
"""
from analysis.classifier import run

__all__ = ["run"]
