"""delivery/ — Camada de Entrega (Fase 4).

Renderiza o MESMO objeto Briefing para Telegram, DOCX e Google Sheets.
Cada adaptador isolado e testável.
"""
from delivery import telegram, docx_writer, sheets

__all__ = ["telegram", "docx_writer", "sheets"]
