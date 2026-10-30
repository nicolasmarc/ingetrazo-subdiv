"""The panel's texts: English by default, French or Spanish when IngeTrazo is in that language;
the Create help text names the document's unit, not metres."""
import re

from subdiv import lang, ops
from subdiv.lang_es import ES
from subdiv.lang_fr import FR


def _texts():
    out = []
    for s in ops.TOOL_SPECS:
        out += [s.label, s.tip] + ([s.value_label] if s.value_label else [])
    return out


def test_create_tip_names_the_unit_of_the_document():
    tip = ops.SPECS["create"].tip
    assert "{unit}" in tip and "metre" not in tip
    assert lang.T(tip, unit="millimetres").startswith("New box cage (size in millimetres)")
    for s in ops.TOOL_SPECS:                  # no other help text names a unit
        assert not re.search(r"\b(metres?|meters?|mm|inch(es)?)\b", s.tip), s.key


def test_french_follows_the_language_and_keeps_placeholders():
    lang.set_language("fr")
    try:
        assert lang.T("Apply") == "Appliquer"
        assert lang.T(ops.SPECS["create"].tip, unit=lang.T("inches")).startswith(
            "Nouvelle cage en boîte (taille en pouces)")
        assert lang.T("Converted: {n} faces, {k} sharp edges", n=12, k=3) == \
            "Converti : 12 faces, 3 arêtes vives"
        assert ops.describe(("e", 3, 4)) == "Arête 3-4"
        for t in _texts():
            assert t in FR, t
    finally:
        lang.set_language(None)
    assert lang.T("Apply") == "Apply"
    for k, v in FR.items():
        assert set(re.findall(r"{(\w+)}", k)) == set(re.findall(r"{(\w+)}", v)), k
        assert k.count("%d") == v.count("%d"), k


def test_english_is_the_default_outside_ingetrazo(monkeypatch):
    monkeypatch.delenv("SUBD_LANG", raising=False)
    assert lang.language() in ("en", "fr")      # IngeTrazo decides when present
    monkeypatch.setenv("SUBD_LANG", "fr")
    assert lang.T("Finish") == "Terminer"


def test_spanish_follows_the_language():
    lang.set_language("es")
    try:
        assert lang.T("Apply") == "Aplicar"
        assert lang.T(ops.SPECS["create"].tip, unit=lang.T("millimetres")).startswith(
            "Nueva jaula en forma de caja (tamaño en milímetros)")
        assert lang.T("Converted: {n} faces, {k} sharp edges", n=12, k=3) == \
            "Convertido: 12 caras, 3 aristas vivas"
        assert ops.describe(("e", 3, 4)) == "Arista 3-4"
        for t in _texts():
            assert t in ES, t
    finally:
        lang.set_language(None)
    assert lang.T("Apply") == "Apply"


def test_every_language_has_every_text_with_the_same_placeholders():
    # Spanish and French carry exactly the same texts, none empty, no stray placeholder.
    assert set(ES) == set(FR), sorted(set(ES) ^ set(FR))
    for name, table in (("fr", FR), ("es", ES)):
        for k, v in table.items():
            assert v.strip(), (name, k)
            assert set(re.findall(r"{(\w+)}", k)) == set(re.findall(r"{(\w+)}", v)), (name, k)
            assert k.count("%d") == v.count("%d"), (name, k)
            assert k.count("\n") == v.count("\n"), (name, k)


def test_texts_used_by_the_code_are_all_translated():
    # Every literal passed to T() in the sources has a French and a Spanish text.
    import ast
    import pathlib
    root = pathlib.Path(lang.__file__).parent
    missing = set()
    for f in ("panel.py", "ops.py", "edit.py", "group.py"):
        tree = ast.parse((root / f).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("T", "_T")
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                text = node.args[0].value
                if text and (text not in FR or text not in ES):
                    missing.add(text)
    assert not missing, sorted(missing)


def test_language_codes_are_normalised(monkeypatch):
    import sys, types
    for code, want in (("es", "es"), ("es-MX", "es"), ("es_ES", "es"), ("fr", "fr"),
                       ("fr-CA", "fr"), ("pt-BR", "en"), ("en", "en"), ("", "en")):
        mod = types.ModuleType("core.i18n"); mod.current_language = lambda c=code: c
        monkeypatch.setitem(sys.modules, "core", types.ModuleType("core"))
        monkeypatch.setitem(sys.modules, "core.i18n", mod)
        monkeypatch.delenv("SUBD_LANG", raising=False)
        assert lang.language() == want, code
    monkeypatch.setenv("SUBD_LANG", "es")
    assert lang.T("Finish") == "Terminar"
