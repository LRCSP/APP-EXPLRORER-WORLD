"""Marcadores de mercado (cotações do dia) — fonte gratuita Yahoo Finance.

Outro tipo de sinal (números, não notícia). Busca uma lista configurável de
símbolos e devolve {nome, valor, variacao_pct, fonte}. Tolera símbolo fora do ar.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass

import requests

log = logging.getLogger("market")

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_UA = "GeoIntelMonitor/0.1 (+https://example.com)"


def _get_json(url: str, timeout: int = 15, retries: int = 3) -> dict:
    """GET com retry e backoff exponencial (0.5s, 1s, 2s)."""
    erro = None
    for tentativa in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": _UA}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # rede/HTTP/JSON
            erro = e
            if tentativa < retries - 1:
                time.sleep(0.5 * (2 ** tentativa))
    raise erro if erro else RuntimeError("falha desconhecida")


def _closes(meta_result: dict) -> list[float]:
    """Extrai fechamentos finitos (descarta None/NaN/inf)."""
    q = meta_result["indicators"]["quote"][0]["close"]
    return [round(c, 4) for c in q if c is not None and math.isfinite(c)]

# Marcadores padrão (nome legível -> símbolo Yahoo). Configurável.
PADRAO: dict[str, str] = {
    "Dólar (USD/BRL)": "USDBRL=X",
    "Euro (EUR/BRL)": "EURBRL=X",
    "Ibovespa": "^BVSP",
    "Petróleo Brent": "BZ=F",
    "Bitcoin (USD)": "BTC-USD",
}


@dataclass
class MarketQuote:
    nome: str
    simbolo: str
    valor: float
    variacao_pct: float | None
    fonte: str = "Yahoo Finance"

    @property
    def resumo(self) -> str:
        v = f"{self.valor:,.2f}"
        if self.variacao_pct is None:
            return f"{self.nome}: {v}"
        return f"{self.nome}: {v} ({self.variacao_pct:+.2f}%)"


def fetch_series(simbolo: str, intervalo: str = "1mo", timeout: int = 15) -> list[float]:
    """Série de fechamentos (finitos) do período. Levanta em falha total."""
    url = YAHOO.format(symbol=simbolo) + f"?range={intervalo}&interval=1d"
    data = _get_json(url, timeout=timeout)
    return _closes(data["chart"]["result"][0])


def fetch_quote(nome: str, simbolo: str, timeout: int = 15) -> MarketQuote | None:
    try:
        data = _get_json(YAHOO.format(symbol=simbolo), timeout=timeout)
        meta = data["chart"]["result"][0]["meta"]
        preco = meta.get("regularMarketPrice")
        ant = meta.get("chartPreviousClose") or meta.get("previousClose")
        if preco is None or not math.isfinite(preco):
            return None
        var = ((preco - ant) / ant * 100) if (ant and math.isfinite(ant)) else None
        return MarketQuote(nome=nome, simbolo=simbolo, valor=float(preco),
                           variacao_pct=round(var, 2) if var is not None else None)
    except Exception as e:
        log.warning("cotação falhou %s (%s): %s", nome, simbolo, e)
        return None


def fetch_markets(simbolos: dict[str, str] | None = None) -> list[MarketQuote]:
    """Busca todas as cotações. Símbolo fora do ar é ignorado, não derruba o resto."""
    simbolos = simbolos or PADRAO
    cotacoes = []
    for nome, sym in simbolos.items():
        q = fetch_quote(nome, sym)
        if q:
            cotacoes.append(q)
    return cotacoes
