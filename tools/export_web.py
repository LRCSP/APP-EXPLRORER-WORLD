"""Exporta um snapshot do briefing (3 perfis × PT/EN) + mercado para o site.

Gera web/index.html (autossuficiente, a partir de web/template.html) e
web/data.json. Roda com o cérebro configurado (Gemini/OpenRouter/Anthropic) ou
em DEMO. Uso:
    python -m tools.export_web [--top-n 6]
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import requests

from config.loader import Settings, load_profiles
import ingest
import analysis
from analysis.profiles import rank_for_profile
from analysis.validators import safe_url
from impact.engine import montar_briefings


def inline_json(data: dict) -> str:
    """JSON seguro para embutir dentro de <script>: neutraliza </, U+2028/9."""
    s = json.dumps(data, ensure_ascii=False)
    return (s.replace("</", "<\\/")
             .replace(" ", "\\u2028")
             .replace(" ", "\\u2029"))

log = logging.getLogger("export_web")
ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

MARKET = [
    {"key": "USD",   "name": "Dólar · USD/BRL",   "sym": "USDBRL=X", "pre": "R$ ",  "dec": 2, "unit": {"pt": "reais por US$ 1", "en": "BRL per US$ 1"}},
    {"key": "EUR",   "name": "Euro · EUR/BRL",    "sym": "EURBRL=X", "pre": "R$ ",  "dec": 2, "unit": {"pt": "reais por € 1", "en": "BRL per € 1"}},
    {"key": "IBOV",  "name": "Ibovespa",          "sym": "^BVSP",    "pre": "",     "dec": 0, "unit": {"pt": "pontos", "en": "index points"}},
    {"key": "BRENT", "name": "Petróleo Brent",    "sym": "BZ=F",     "pre": "US$ ", "dec": 2, "unit": {"pt": "US$ por barril", "en": "US$ per barrel"}},
    {"key": "CAFE",  "name": "Café · ICE",        "sym": "KC=F",     "pre": "",     "dec": 1, "unit": {"pt": "US¢ por libra-peso", "en": "US¢ per pound"}},
    {"key": "SOJA",  "name": "Soja · CBOT",       "sym": "ZS=F",     "pre": "",     "dec": 1, "unit": {"pt": "US¢ por bushel", "en": "US¢ per bushel"}},
]


def _serie(sym: str) -> list[float]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d"
    r = requests.get(url, headers={"User-Agent": "GeoIntelMonitor/0.1"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    return [round(c, 4) for c in res["indicators"]["quote"][0]["close"] if c is not None]


def fetch_market() -> list[dict]:
    out = []
    for m in MARKET:
        try:
            s = _serie(m["sym"])
            if len(s) < 2:
                continue
            out.append({
                "name": m["name"], "unit": m["unit"], "pre": m["pre"], "dec": m["dec"],
                "value": s[-1], "pct": round((s[-1] - s[0]) / s[0] * 100, 2), "series": s,
            })
        except Exception as e:
            log.warning("mercado %s falhou: %s", m["key"], e)
    return out


def _ev_dict(e) -> dict:
    return {
        "titulo": e.titulo, "resumo": e.resumo, "editoria": e.editoria,
        "geografia": e.geografia, "severidade": e.severidade, "relevancia": e.relevancia,
        "impacto_custo": e.impacto_custo, "impacto_cadeia": e.impacto_cadeia,
        "exposicao_cyber": e.exposicao_cyber, "acao_recomendada": e.acao_recomendada,
        "fonte": e.fonte, "url": safe_url(e.url), "idioma_original": e.idioma_original,
        "titulo_original": e.titulo_original,
    }


def build_data(top_n: int) -> dict:
    settings = Settings.from_env()
    idiomas = settings.idiomas or ["pt", "en"]
    perfis = load_profiles()

    log.info("Ingestão + classificação...")
    eventos, _ = ingest.run()
    rankeados = analysis.run(eventos, settings)

    profiles_out = []
    for p in perfis:
        log.info("Perfil %s...", p.id)
        sel = rank_for_profile(rankeados, p, settings.max_per_source, settings.max_per_sector)
        briefs = montar_briefings(sel, settings, top_n, len(eventos), lente=p.lente,
                                  titulos={l: p.nome_de(l) for l in idiomas})
        profiles_out.append({
            "id": p.id,
            "name": {l: p.nome_de(l) for l in idiomas},
            "desc": {l: p.descricao.get(l, "") for l in idiomas},
            "events": {l: [_ev_dict(e) for e in briefs[l].eventos] for l in idiomas},
        })

    from datetime import datetime, timezone
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profiles": profiles_out,
        "market": fetch_market(),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=6)
    args = ap.parse_args()

    data = build_data(args.top_n)
    (WEB / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    template = (WEB / "template.html").read_text(encoding="utf-8")
    html = template.replace("DATA_PLACEHOLDER", inline_json(data))
    (WEB / "index.html").write_text(html, encoding="utf-8")

    n = sum(len(p["events"].get("pt", [])) for p in data["profiles"])
    log.info("OK: %d perfis, %d eventos (pt), %d ativos de mercado -> web/index.html",
             len(data["profiles"]), n, len(data["market"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
