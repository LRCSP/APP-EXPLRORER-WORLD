from tools.export_web import inline_json


def test_inline_json_neutraliza_script():
    out = inline_json({"x": "</script><img src=x onerror=alert(1)>"})
    assert "</script>" not in out
    assert "</" not in out           # todo '</' foi escapado
    assert "<\\/script>" in out


def test_inline_json_line_separators():
    out = inline_json({"x": "a" + chr(0x2028) + "b" + chr(0x2029) + "c"})
    assert chr(0x2028) not in out
    assert chr(0x2029) not in out
    assert "\\u2028" in out and "\\u2029" in out


def test_inline_json_roundtrip_json():
    import json
    payload = {"a": 1, "b": "texto com </tag> e acento çã"}
    out = inline_json(payload)
    # desfaz o escape de </ para reparsear e conferir integridade
    assert json.loads(out.replace("<\\/", "</")) == payload
