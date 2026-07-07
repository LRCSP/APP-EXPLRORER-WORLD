"""Mapeamento de setor (backend) -> editoria pública bilíngue (PT/EN).

O backend mantém o `setor` técnico (ex.: "cyber"), mas a renderização pública
usa rótulos de editoria. Em especial, "cyber" NÃO aparece como editoria
principal: vira "Segurança Digital" dentro de "Tecnologia & Inovação".
"""
from __future__ import annotations

EDITORIAS: dict[str, dict[str, str]] = {
    "energia":       {"pt": "Energia",                "en": "Energy"},
    "petroleo":      {"pt": "Petróleo",               "en": "Oil"},
    "cyber":         {"pt": "Segurança Digital",      "en": "Digital Security"},
    "tecnologia":    {"pt": "Tecnologia & Inovação",  "en": "Technology & Innovation"},
    "fertilizantes": {"pt": "Fertilizantes",          "en": "Fertilizers"},
    "alimentos":     {"pt": "Alimentos",              "en": "Food"},
    "insumos":       {"pt": "Insumos",                "en": "Raw Materials"},
    "exportacoes":   {"pt": "Comércio Exterior",      "en": "Foreign Trade"},
    "economia":      {"pt": "Economia",               "en": "Economy"},
    "geopolitica":   {"pt": "Geopolítica",            "en": "Geopolitics"},
}

# Editoria "guarda-chuva": Segurança Digital é subeditoria de Tecnologia & Inovação.
GUARDA_CHUVA = {"cyber": "tecnologia"}


def rotulo(setor: str, lang: str = "pt") -> str:
    """Rótulo público da editoria no idioma pedido (fallback: o próprio setor)."""
    return EDITORIAS.get(setor, {}).get(lang, setor.capitalize())
