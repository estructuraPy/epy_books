"""The GUI shell catalog and its callbacks."""

from __future__ import annotations

from epy_books._core import _i18n


def test_language_switch_and_values() -> None:
    seen: list[str] = []
    _i18n.on_language_changed(
        lambda: seen.append(_i18n.current_language())
    )
    _i18n.set_language('en')
    assert _i18n.tr('app') == 'ePy Books'
    _i18n.set_language('en')
    _i18n.set_language('fr')
    assert seen
    _i18n.set_language('es')
    assert _i18n.tr('open') == 'Abrir libro'
    assert _i18n.text('validate') == 'Validar'
    assert (
        _i18n.tr('Could not open: {error}', error='x')
        == 'No se pudo abrir: x'
    )
    assert _i18n.current_language() in {'es', 'en'}

