from analysis.validators import (
    clamp_severidade, clamp_relevancia, validate_impact_block,
    validate_classification, safe_url,
)


def test_clamp_severidade():
    assert clamp_severidade(9) == 5
    assert clamp_severidade(0) == 1
    assert clamp_severidade("3") == 3
    assert clamp_severidade("lixo") == 1
    assert clamp_severidade(None) == 1
    assert clamp_severidade(4.7) == 5


def test_clamp_relevancia():
    assert clamp_relevancia(99) == 10
    assert clamp_relevancia(-5) == 1
    assert clamp_relevancia(7) == 7
    assert clamp_relevancia("") == 1


def test_impact_block_incompleto():
    limpo, faltando = validate_impact_block({"impacto_custo": "ok"})
    assert limpo["impacto_custo"] == "ok"
    assert "impacto_cadeia" in faltando
    _, faltando_vazio = validate_impact_block({})
    assert "impacto:vazio" in faltando_vazio


def test_safe_url():
    assert safe_url("http://x.com") == "http://x.com"
    assert safe_url("https://y.com/a") == "https://y.com/a"
    assert safe_url("javascript:alert(1)") == "#"
    assert safe_url("data:text/html,x") == "#"
    assert safe_url("") == "#"
    assert safe_url(None) == "#"


def test_validate_classification_fallback():
    class E:
        titulo = "Título Original"
        setor = "cyber"

    setores = ["cyber", "energia"]
    campos, avisos = validate_classification(
        {"setor": "inexistente", "severidade": "9", "relevancia": "50",
         "titulo_pt": "", "titulo_en": "EN title"},
        E(), setores,
    )
    assert campos["setor"] == "cyber"          # setor inválido -> fallback do evento
    assert campos["severidade"] == 5            # clamp
    assert campos["relevancia"] == 10           # clamp
    assert campos["titulo_i18n"]["pt"] == "Título Original"  # vazio -> original
    assert campos["titulo_i18n"]["en"] == "EN title"
    assert avisos  # gerou avisos
