"""Book editor tab: structure, profile and design controls."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from epy_books import Book, DesignSpec, available_designs, available_profiles
from epy_books._core import _i18n as i18n
from epy_books._ui.design_dialog import DesignDialog


class BookTab(QWidget):
    """One open book project."""

    def __init__(self, path: str | Path) -> None:
        """Open a book and build its controls."""
        super().__init__()
        self.path = Path(path)
        self.book = Book.from_file(self.path)
        self.setWindowTitle(self.book.manifest.title)
        self._texts: list[tuple[Callable[[str], None], str]] = []

        title = QLabel(f"<h2>{self.book.manifest.title}</h2>")
        subtitle = QLabel(self.book.manifest.subtitle)
        subtitle.setWordWrap(True)

        self.profile = QComboBox()
        for profile_id, name in available_profiles():
            self.profile.addItem(name, profile_id)
        self.profile.setCurrentIndex(
            max(0, self.profile.findData(self.book.profile_id))
        )

        self.design = QComboBox()
        for design_id, name in available_designs():
            self.design.addItem(name, design_id)
        self.design.setCurrentIndex(
            max(0, self.design.findData(self.book.design_id))
        )

        controls = QHBoxLayout()
        controls.addWidget(self._lbl("Profile"))
        controls.addWidget(self.profile)
        controls.addWidget(self._lbl("Design"))
        controls.addWidget(self.design)

        self.chapters = QTableWidget(0, 3)
        self.chapters.setHorizontalHeaderLabels(
            ["#", i18n.tr("Chapter"), i18n.tr("File")]
        )
        self.chapters.horizontalHeader().setStretchLastSection(True)
        self.chapters.itemSelectionChanged.connect(self._show_chapter)
        for row, chapter in enumerate(self.book.manifest.chapters):
            self.chapters.insertRow(row)
            values = (
                str(chapter.number or ""),
                chapter.title,
                chapter.name,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.chapters.setItem(row, column, item)

        self.validate = self._btn("Validate")
        self.validate.clicked.connect(self._validate)
        self.export = self._btn("Export PDF")
        self.export.clicked.connect(self._export_pdf)
        self.design_button = self._btn("Design...")
        self.design_button.clicked.connect(self._edit_design)
        actions = QHBoxLayout()
        actions.addWidget(self.validate)
        actions.addWidget(self.design_button)
        actions.addWidget(self.export)
        actions.addStretch(1)

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.chapters)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addWidget(split, 1)
        layout.addLayout(actions)

    def _lbl(self, key: str) -> QLabel:
        label = QLabel(i18n.tr(key))
        self._texts.append((label.setText, key))
        return label

    def _btn(self, key: str) -> QPushButton:
        button = QPushButton(i18n.tr(key))
        self._texts.append((button.setText, key))
        return button

    def retranslate(self) -> None:
        """Relabel the controls after a language change."""
        for setter, key in self._texts:
            setter(i18n.tr(key))
        self.chapters.setHorizontalHeaderLabels(
            ["#", i18n.tr("Chapter"), i18n.tr("File")]
        )

    def _show_chapter(self) -> None:
        row = self.chapters.currentRow()
        if row < 0 or row >= len(self.book.manifest.chapters):
            return
        chapter = self.book.manifest.chapters[row]
        try:
            text = self.book.text_for(chapter.source)
        except FileNotFoundError:
            text = ""
        self.preview.setMarkdown(text or i18n.tr("No content."))

    def close(self) -> None:
        """Close the book store when the tab is closed."""
        self.book.close()

    def _validate(self) -> None:
        profile_id = str(self.profile.currentData())
        result = self.book.validate(profile_id)
        if result.ok:
            QMessageBox.information(
                self,
                i18n.tr("Validation"),
                i18n.tr("The book passes."),
            )
            return
        QMessageBox.warning(
            self,
            i18n.tr("Validation"),
            "\n".join(item.message for item in result),
        )

    def _edit_design(self) -> None:
        current = self.book.design(str(self.design.currentData()))
        dialog = DesignDialog(current.to_epy_docs())
        if dialog.exec() != DesignDialog.Accepted:
            return
        payload = dialog.payload(current.to_epy_docs())
        updated = DesignSpec.from_row(
            {
                **payload,
                "id": current.id,
                "name": current.name,
                "description": current.description,
                "layout_style": current.layout_style,
            }
        )
        self.book.apply_design(updated)
        QMessageBox.information(
            self, i18n.tr("Design"), i18n.tr("Design updated.")
        )

    def _export_pdf(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            i18n.tr("Export PDF"),
            f"{self.book.manifest.stem}.pdf",
            "PDF (*.pdf)",
        )
        if not target:
            return
        try:
            self.book.to_pdf(target, design=str(self.design.currentData()))
        except Exception as exc:
            QMessageBox.critical(self, i18n.tr("Export PDF"), str(exc))
            return
        QMessageBox.information(
            self, i18n.tr("Export PDF"), i18n.tr("PDF generated.")
        )
