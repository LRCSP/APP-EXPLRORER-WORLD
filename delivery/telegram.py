"""Adaptador de entrega: Telegram.

- render(): transforma o Briefing em mensagens de texto (HTML), dividindo
  automaticamente quando passa do limite de 4096 caracteres do Telegram.
- send(): envia via Bot API (requests). Sem token -> levanta erro claro.

Testável sozinho: render() é puro e não toca a rede.
"""
from __future__ import annotations

import html
import logging
import re

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
    editoria = getattr(ev, "editoria", "") or ev.setor
    linhas = [
        f"{sev} <b>{_esc(ev.titulo)}</b>",
        f"<i>{_esc(editoria)} · {_esc(ev.geografia)} · sev {ev.severidade}/5 · relev {ev.relevancia}/10</i>",
    ]
    if getattr(ev, "resumo", ""):
        linhas.append(f"📝 {_esc(ev.resumo)}")
    if getattr(ev, "projecao", ""):
        linhas.append(f"🔮 <b>Cenário:</b> {_esc(ev.projecao)}")
    linhas += [
        f"💰 <b>Custo:</b> {_esc(ev.impacto_custo)}",
        f"🔗 <b>Cadeia:</b> {_esc(ev.impacto_cadeia)}",
        f"🛡️ <b>Cyber:</b> {_esc(ev.exposicao_cyber)}",
        f"✅ <b>Ação:</b> {_esc(ev.acao_recomendada)}",
    ]
    if ev.url:
        idi = (getattr(ev, "idioma_original", "") or "").upper()
        selo = f" [{idi}]" if idi else ""
        linhas.append(f'<a href="{_esc(ev.url)}">fonte: {_esc(ev.fonte)}{selo}</a>')
    return "\n".join(linhas)


_TAG = re.compile(r"<[^>]+>")


def _strip_tags(s: str) -> str:
    """Remove tags HTML (fallback texto puro) para blocos gigantes."""
    return html.unescape(_TAG.sub("", s)).strip()


def _split_plain(texto: str, limite: int = LIMITE) -> list[str]:
    """Quebra texto PURO em pedaços <= limite, em fronteiras de palavra."""
    partes: list[str] = []
    atual = ""
    for palavra in texto.split():
        if len(atual) + len(palavra) + 1 > limite:
            if atual:
                partes.append(atual)
                atual = palavra
            else:  # palavra única maior que o limite
                partes.append(palavra[:limite])
                atual = palavra[limite:]
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        partes.append(atual)
    return partes or [""]


def render(briefing: Briefing) -> list[str]:
    """Devolve mensagens (cada uma <= 4096 chars).

    Divide por BLOCOS (evento). Um bloco que sozinho passe do limite vira texto
    puro (sem tags) e, se ainda passar, é quebrado por palavra — nunca corta
    uma tag HTML no meio.
    """
    cabecalho = (
        f"📡 <b>{_esc(briefing.titulo)}</b>\n"
        f"<i>{_esc(briefing.gerado_em)} · {len(briefing.eventos)} eventos · "
        f"modo {briefing.modo}</i>"
    )
    brutos = [cabecalho] + [_bloco_evento(ev, i) for i, ev in enumerate(briefing.eventos, 1)]

    # Blocos grandes demais: fallback texto puro (pode virar vários pedaços).
    blocos: list[str] = []
    for b in brutos:
        if len(b) <= LIMITE:
            blocos.append(b)
        else:
            blocos.extend(_split_plain(_strip_tags(b)))

    mensagens: list[str] = []
    atual = ""
    for bloco in blocos:
        candidato = bloco if not atual else f"{atual}\n\n{bloco}"
        if len(candidato) > LIMITE and atual:
            mensagens.append(atual)
            atual = bloco
        else:
            atual = candidato
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
