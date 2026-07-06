from delivery.telegram import render, LIMITE, _split_plain, _strip_tags
from impact.models import Briefing, EventoBriefing


def _ev(**kw):
    base = dict(titulo="Título", fonte="Fonte", url="http://x.com", data="",
                setor="cyber", geografia="Global", severidade=5, relevancia=10,
                impacto_custo="c", impacto_cadeia="d", exposicao_cyber="e",
                acao_recomendada="f", editoria="Segurança Digital",
                idioma_original="en", resumo="resumo")
    base.update(kw)
    return EventoBriefing(**base)


def test_strip_tags():
    assert _strip_tags("<b>oi</b> &amp; tchau") == "oi & tchau"


def test_split_plain_respeita_limite():
    partes = _split_plain("palavra " * 5000, limite=100)
    assert all(len(p) <= 100 for p in partes)


def test_render_muitos_eventos_dentro_do_limite():
    b = Briefing.novo()
    for i in range(30):
        b.eventos.append(_ev(titulo=f"Evento {i}"))
    msgs = render(b)
    assert msgs and all(len(m) <= LIMITE for m in msgs)


def test_bloco_gigante_vira_texto_puro_sem_cortar_tag():
    b = Briefing.novo()
    b.eventos.append(_ev(impacto_custo="X " * 4000))  # força > 4096
    msgs = render(b)
    assert all(len(m) <= LIMITE for m in msgs)
    # nenhuma mensagem termina com uma tag aberta ('<' depois do último '>')
    for m in msgs:
        assert m.rfind("<") <= m.rfind(">")
