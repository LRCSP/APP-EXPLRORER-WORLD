from ingest.schema import Evento
from analysis.diversity import diversify


def _mk(titulo, fonte, setor, rel):
    e = Evento(titulo=titulo, fonte=fonte, url=f"http://x/{titulo.replace(' ', '')}",
               data="", setor=setor, texto_bruto=titulo)
    e.extra = {"relevancia": rel, "severidade": 3, "setor": setor}
    return e


def test_limite_por_fonte():
    titulos = ["ataque russia gasoduto", "vazamento dados banco", "sancao china chips",
               "bloqueio porto grego", "fraude cambio internacional"]
    evs = [_mk(t, "F1", "cyber", 10) for t in titulos]
    out = diversify(evs, max_por_fonte=2, max_por_setor=10)
    assert len(out) == 5                       # títulos distintos: nada descartado
    assert sum(1 for e in out[:2] if e.fonte == "F1") == 2  # no topo, no máx. 2 da F1


def test_limite_por_setor():
    titulos = ["ransomware hospital europa", "phishing banco asiatico",
               "malware industria naval", "invasao rede eletrica", "roubo credenciais nuvem"]
    evs = ([_mk(t, f"F{i}", "cyber", 10) for i, t in enumerate(titulos)]
           + [_mk("preco energia dispara", "FE", "energia", 9)])
    out = diversify(evs, max_por_fonte=5, max_por_setor=3)
    topo = out[:4]
    assert sum(1 for e in topo if e.extra["setor"] == "cyber") <= 3


def test_dedup_titulos_parecidos():
    a = _mk("CISA adiciona vulnerabilidade explorada ao catalogo", "F1", "cyber", 10)
    b = _mk("CISA adiciona vulnerabilidade explorada ao catalogo hoje", "F2", "cyber", 9)
    out = diversify([a, b], max_por_fonte=5, max_por_setor=5)
    assert len(out) == 1                       # quase-duplicata removida
