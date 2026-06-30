"""Provedores de LLM atrás de uma interface comum (Gemini / Anthropic).

A análise (Fase 2) e o impacto (Fase 3) só conhecem `Brain.complete(...)`.
Trocar de provedor é só configuração no .env — nenhuma das outras camadas muda.
"""
from __future__ import annotations

import logging

from config.loader import Settings

log = logging.getLogger("brain")


class Brain:
    """Interface comum. `complete` devolve texto (idealmente JSON quando json=True)."""
    name = "base"

    def complete(self, system: str, prompt: str, max_tokens: int = 800, json: bool = False) -> str:
        raise NotImplementedError


class GeminiBrain(Brain):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def complete(self, system, prompt, max_tokens=800, json=False):
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if json else "text/plain",
        )
        resp = self._client.models.generate_content(model=self._model, contents=prompt, config=cfg)
        return resp.text or ""


class AnthropicBrain(Brain):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system, prompt, max_tokens=800, json=False):
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


def _resolver_provedor(settings: Settings) -> str:
    provider = (settings.llm_provider or "auto").lower()
    if provider != "auto":
        return provider
    if settings.gemini_api_key:
        return "gemini"
    if settings.anthropic_api_key:
        return "anthropic"
    return "demo"


def make_brain(settings: Settings, fast: bool = False) -> Brain | None:
    """Cria o cérebro conforme o .env. `fast=True` pede o modelo mais barato.

    Devolve None quando não há provedor configurado (modo DEMO).
    """
    provider = _resolver_provedor(settings)
    try:
        if provider == "gemini" and settings.gemini_api_key:
            return GeminiBrain(settings.gemini_api_key, settings.gemini_model)
        if provider == "anthropic" and settings.anthropic_api_key:
            model = settings.anthropic_model_fast if fast else settings.anthropic_model
            return AnthropicBrain(settings.anthropic_api_key, model)
    except Exception as e:  # SDK ausente / chave inválida -> DEMO
        log.warning("cérebro '%s' indisponível (%s); usando modo DEMO", provider, e)
    return None
