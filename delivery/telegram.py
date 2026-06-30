"""Adaptador de entrega: Telegram.

- render(): transforma o Briefing em mensagens de texto (HTML), dividindo
  automaticamente quando passa do limite de 4096 caracteres do Telegram.
- send(): envia via Bot API (requests). Sem token -> levanta erro claro.

Testável sozinho: render() é puro e não toca a rede.
"""
from __future__ import annotations

import html
import logging

import requests

from config.loader import Settings
from impact.models import Briefing

log = logging.getLogger("delivery.telegram")

LIMITE = 4096
_SEV = {1: "🟢", 2: "🟢", 3: "🟡", 4: "🟠", 5: "🔴"}


def _esc(t: str) -> str:
    return html.escape(t or "")


def _bloco_evento(ev, idx: int) -> str:
    sev = _SEV.get(ev.severidade, "⚪")
    linhas = [
        f"{sev} <b>{_esc(ev.titulo)}</b>",
        f"<i>{_esc(ev.setor)} · {_esc(ev.geografia)} · sev {ev.severidade}/5 · relev {ev.relevancia}/10</i>",
        f"💰 <b>Custo:</b> {_esc(ev.impacto_custo)}",
        f"🔗 <b>Cadeia:</b> {_esc(ev.impacto_cadeia)}",
        f"🛡️ <b>Cyber:</b> {_esc(ev.exposicao_cyber)}",
        f"✅ <b>Ação:</b> {_esc(ev.acao_recomendada)}",
    ]
    if ev.url:
        linhas.append(f'<a href="{_esc(ev.url)}">fonte: {_esc(ev.fonte)}</a>')
    return "\n".join(linhas)


def render(briefing: Briefing) -> list[str]:
    """Devolve uma lista de mensagens (cada uma <= 4096 chars)."""
    cabecalho = (
        f"📡 <b>{_esc(briefing.titulo)}</b>\n"
        f"<i>{_esc(briefing.gerado_em)} · {len(briefing.eventos)} eventos · "
        f"modo {briefing.modo}</i>"
    )
    blocos = [cabecalho] + [_bloco_evento(ev, i) for i, ev in enumerate(briefing.eventos, 1)]

    mensagens: list[str] = []
    atual = ""
    for bloco in blocos:
        candidato = bloco if not atual else f"{atual}\n\n{bloco}"
        if len(candidato) > LIMITE and atual:
            mensagens.append(atual)
            atual = bloco
        else:
            atual = candidato
        # bloco isolado maior que o limite: corta com segurança
        while len(atual) > LIMITE:
            mensagens.append(atual[:LIMITE])
            atual = atual[LIMITE:]
    if atual:
        mensagens.append(atual)
    return mensagens


def send(briefing: Briefing, settings: Settings | None = None) -> int:
    """Envia o briefing ao chat configurado. Retorna nº de mensagens enviadas."""
    settings = settings or Settings.from_env()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes. Preencha o .env para enviar."
        )
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    enviadas = 0
    for msg in render(briefing):
        resp = requests.post(
            url,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        enviadas += 1
    log.info("Telegram: %d mensagens enviadas", enviadas)
    return enviadas
