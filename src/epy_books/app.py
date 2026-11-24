"""ePy Books GUI: one tab per open book project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from epy_export import ORGANIZATION, apply_chrome
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from epy_books._core import _i18n as i18n
from epy_books.epy_studio_connect import launch_hint, register, unregister

APP_NAME = "epy_books"
FILE_FILTER = "Libro (*.json *.kepy);;Todos los archivos (*)"


class BookWindow(QMainWindow):
    """Main window with one tab per open book."""

    def __init__(self) -> None:
        """Build the window, toolbar and tab bar."""
        super().__init__()
        self.setWindowTitle(i18n.text("app"))
        self.resize(1280, 820)
        self.setWindowIcon(QIcon())
        self._settings = QSettings(ORGANIZATION, APP_NAME)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)
        self._build_toolbar()
        self.statusBar().showMessage("Listo")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        open_action = QAction(i18n.text("open"), self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_dialog)
        toolbar.addAction(open_action)
        validate_action = QAction(i18n.text("validate"), self)
        validate_action.triggered.connect(self._validate_current)
        toolbar.addAction(validate_action)

    def open_dialog(self) -> None:
        """Ask for a project file and open it."""
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.text("open"), str(Path.home()), FILE_FILTER
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        """Open a book project in a new tab."""
        from epy_books._ui.tab import BookTab

        try:
            tab = BookTab(path)
        except Exception as exc:
            QMessageBox.critical(self, i18n.text("open"), str(exc))
            return
        index = self.tabs.addTab(tab, tab.book.manifest.title)
        self.tabs.setCurrentIndex(index)
        self.statusBar().showMessage(str(path))

    def _validate_current(self) -> None:
        tab = self.tabs.currentWidget()
        if tab is not None and hasattr(tab, "_validate"):
            tab._validate()

    def _close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if widget is not None:
            if hasattr(widget, "close"):
                widget.close()
            widget.deleteLater()
        self.tabs.removeTab(index)


def main(argv: list[str] | None = None) -> int:
    """Run the ePy Books application."""
    parser = argparse.ArgumentParser(prog="epy_books")
    parser.add_argument("files", nargs="*", help="Libros a abrir.")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--unregister", action="store_true")
    args = parser.parse_args(argv)
    if args.version:
        from epy_books import __version__

        print(f"epy_books {__version__}")
        return 0
    if args.unregister:
        for line in unregister():
            print(line)
        return 0
    if args.register:
        for line in register(argv):
            print(line)
        print(launch_hint())
        return 0
    instance = QApplication.instance()
    if isinstance(instance, QApplication):
        app = instance
    else:
        app = QApplication(sys.argv)
    apply_chrome(app)
    window = BookWindow()
    for path in args.files:
        window.open_path(path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
