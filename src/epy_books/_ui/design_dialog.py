"""Small interior-design dialog for the book tab."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
)

_PAGES = {
    "Carta 8.5 x 11": (8.5, 11.0),
    "A4 8.27 x 11.69": (8.27, 11.69),
    "7 x 10": (7.0, 10.0),
    "6 x 9": (6.0, 9.0),
    "5.5 x 8.5": (5.5, 8.5),
}


class DesignDialog(QDialog):
    """Choose page size, margins and the main book toggles."""

    def __init__(self, design: dict[str, Any]) -> None:
        """Build the dialog from the current design mapping."""
        super().__init__()
        self.setWindowTitle("Diseno interior")
        page = design.get("page") or {}
        margins = design.get("margins") or {}
        typography = design.get("typography") or {}
        components = design.get("components") or {}

        self.page = QComboBox()
        self.page.addItems(list(_PAGES))
        size = (
            float(page.get("width_in") or 8.5),
            float(page.get("height_in") or 11),
        )
        for index, value in enumerate(_PAGES.values()):
            if value == size:
                self.page.setCurrentIndex(index)
                break

        self.top = _margin(margins.get("top_in"))
        self.bottom = _margin(margins.get("bottom_in"))
        self.inside = _margin(margins.get("inside_in"))
        self.outside = _margin(margins.get("outside_in"))
        self.body = QSpinBox()
        self.body.setRange(9, 14)
        self.body.setValue(
            int(round(float(typography.get("body_size_pt") or 11)))
        )
        self.running = QCheckBox("Running heads")
        self.running.setChecked(bool(components.get("running_head", False)))
        self.index = QCheckBox("Indice analitico")
        self.index.setChecked(bool(components.get("index", False)))

        form = QFormLayout(self)
        form.addRow("Pagina", self.page)
        form.addRow("Margen superior", self.top)
        form.addRow("Margen inferior", self.bottom)
        form.addRow("Margen interior", self.inside)
        form.addRow("Margen exterior", self.outside)
        form.addRow("Cuerpo (pt)", self.body)
        form.addRow("", self.running)
        form.addRow("", self.index)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def payload(self, base: dict[str, Any]) -> dict[str, Any]:
        """Return the design mapping with the dialog values applied."""
        width, height = _PAGES[self.page.currentText()]
        data = dict(base)
        data["page"] = {
            **dict(base.get("page") or {}),
            "width_in": width,
            "height_in": height,
        }
        data["margins"] = {
            **dict(base.get("margins") or {}),
            "top_in": self.top.value(),
            "bottom_in": self.bottom.value(),
            "inside_in": self.inside.value(),
            "outside_in": self.outside.value(),
        }
        data["typography"] = {
            **dict(base.get("typography") or {}),
            "body_size_pt": float(self.body.value()),
        }
        data["components"] = {
            **dict(base.get("components") or {}),
            "running_head": self.running.isChecked(),
            "index": self.index.isChecked(),
        }
        return data


def _margin(value: Any) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0.3, 3.0)
    spin.setSingleStep(0.05)
    spin.setDecimals(2)
    spin.setValue(float(value or 1.0))
    return spin
