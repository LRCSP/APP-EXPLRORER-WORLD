"""brain/ — o "cérebro" do produto, isolado atrás de uma única interface.

Permite trocar de provedor (Gemini ou Anthropic) sem tocar na análise/impacto.
Se nenhum provedor estiver configurado, devolve None -> pipeline roda em DEMO.
"""
from brain.providers import Brain, make_brain

__all__ = ["Brain", "make_brain"]
