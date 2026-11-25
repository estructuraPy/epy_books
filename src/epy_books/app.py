"""ePy Books GUI: one tab per open book project."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from epy_export import ORGANIZATION, apply_chrome
from epy_export._ui.app_header import install_header
from epy_export._ui.workflow_guide import WorkflowGuide
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from epy_books._core import _i18n as i18n
from epy_books.epy_studio_connect import launch_hint, register, unregister

APP_NAME = "epy_books"
_STEPS = (
    ("Open", "Open a book project."),
    ("Design", "Choose the profile and the design."),
    ("Write", "Edit the chapters."),
    ("Review", "Validate the manuscript."),
    ("Export", "Render the PDF."),
)
_STAGES = ((0, "Prepare"), (2, "Write"), (4, "Deliver"))


def demo_project_path(language: str = "es") -> Path:
    """Materialize the bundled demo book and return its manifest."""
    code = "en" if str(language).lower().startswith("en") else "es"
    base = os.environ.get("LOCALAPPDATA")
    root = (
        Path(base) if base else Path.home() / "AppData" / "Local"
    )
    target = root / "ePy Suite" / "demo" / "epy_books" / code
    manifest = target / "libro.json"
    if manifest.is_file():
        return manifest
    source = (
        Path(__file__).resolve().parent
        / "_config"
        / "_assets"
        / "demo"
        / code
    )
    shutil.copytree(source, target, dirs_exist_ok=True)
    return manifest


class BookWindow(QMainWindow):
    """Main window with one tab per open book."""

    def __init__(self) -> None:
        """Build the window, toolbar, menu and guide."""
        super().__init__()
        self._settings = QSettings(ORGANIZATION, APP_NAME)
        saved = str(self._settings.value("language", i18n.current_language()))
        i18n.set_language(
            saved if saved in i18n.LANGUAGES else "es"
        )
        self._texts: list[tuple[Callable[[str], None], str]] = []
        self.setWindowTitle(i18n.tr("app"))
        self.resize(1280, 820)
        self.setWindowIcon(QIcon())
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)
        self._build_toolbar()
        self._build_guide()
        self._build_menus()
        self.header = install_header(
            self,
            title="ePy Books",
            subtitle=i18n.tr(
                "Books: editorial design, history and export."
            ),
            guide_dock=self.guide_dock,
            language=i18n.current_language(),
        )
        self.statusBar().showMessage(i18n.tr("Ready"))
        i18n.on_language_changed(self._retranslate)
        self._retranslate()

    def _action(self, key: str, menu=None) -> QAction:
        action = QAction(i18n.tr(key), self)
        self._texts.append((action.setText, key))
        if menu is not None:
            menu.addAction(action)
        return action

    def _menu(self, key: str):
        menu = self.menuBar().addMenu(i18n.tr(key))
        self._texts.append((menu.setTitle, key))
        return menu

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(i18n.tr("Main"))
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self._texts.append((self.toolbar.setWindowTitle, "Main"))
        self.open_action = self._action("Open book...")
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_dialog)
        self.toolbar.addAction(self.open_action)
        self.validate_action = self._action("Validate")
        self.validate_action.triggered.connect(self._validate_current)
        self.toolbar.addAction(self.validate_action)

    def _build_guide(self) -> None:
        self.guide = WorkflowGuide(
            _STEPS,
            _STAGES,
            self._go,
            translate=i18n.tr,
            on_language_changed=i18n.on_language_changed,
        )
        self.guide_dock = QDockWidget(i18n.tr("Step by step"), self)
        self.guide_dock.setObjectName("guide")
        self.guide_dock.setMinimumWidth(330)
        self.guide_dock.setWidget(self.guide)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.guide_dock
        )
        self._texts.append((self.guide_dock.setWindowTitle, "Step by step"))

    def _build_menus(self) -> None:
        file_menu = self.file_menu = self._menu("File")
        self.file_open_action = self._action("Open book...", file_menu)
        self.file_open_action.triggered.connect(self.open_dialog)
        self.demo_action = self._action("Demo", file_menu)
        self.demo_action.triggered.connect(self.open_demo)
        file_menu.addSeparator()
        self.quit_action = self._action("Quit", file_menu)
        self.quit_action.triggered.connect(self.close)
        view = self._menu("View")
        self.language_menu = view.addMenu(i18n.tr("Language"))
        self._texts.append((self.language_menu.setTitle, "Language"))
        self._language_actions: dict[str, QAction] = {}
        for code, name in i18n.LANGUAGES.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(code == i18n.current_language())
            action.setData(code)
            action.triggered.connect(self._set_language)
            self.language_menu.addAction(action)
            self._language_actions[code] = action
        self.guide_action = self._action("Step by step", view)
        self.guide_action.setCheckable(True)
        self.guide_action.setChecked(True)
        self.guide_action.toggled.connect(self.guide_dock.setVisible)
        self.guide_dock.visibilityChanged.connect(self.guide_action.setChecked)
        help_menu = self._menu("Help")
        self.about_action = self._action("About ePy Books", help_menu)
        self.about_action.triggered.connect(self._about)

    def _about(self) -> None:  # pragma: no cover
        QMessageBox.about(
            self,
            i18n.tr("About ePy Books"),
            "ePy Books",
        )

    def _retranslate(self) -> None:
        self.setWindowTitle(i18n.tr("app"))
        for setter, key in self._texts:
            setter(i18n.tr(key))
        self.header.set_language(i18n.current_language())
        self.header.set_texts(
            "ePy Books",
            i18n.tr("Books: editorial design, history and export."),
        )
        for code, action in self._language_actions.items():
            action.setChecked(code == i18n.current_language())
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if hasattr(tab, "retranslate"):
                tab.retranslate()
        if self.tabs.count() == 0:
            self.statusBar().showMessage(i18n.tr("Ready"))

    def _set_language(self) -> None:
        action = self.sender()
        code = (
            str(action.data())
            if action is not None
            else i18n.current_language()
        )
        i18n.set_language(code)
        self._settings.setValue("language", code)

    def _go(self, index: int) -> None:  # pragma: no cover
        """Move to the control of one guide step."""
        tab = self.tabs.currentWidget()
        if index == 0:
            self.open_dialog()
            return
        if tab is None:
            return
        if index == 1 and hasattr(tab, "profile"):
            tab.profile.setFocus()
        elif index == 2 and hasattr(tab, "chapters"):
            tab.chapters.setFocus()
        elif index == 3 and hasattr(tab, "validate"):
            tab.validate.click()
        elif index == 4 and hasattr(tab, "export"):
            tab.export.click()

    def open_dialog(self) -> None:
        """Ask for a project file and open it."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.tr("Open book"),
            str(Path.home()),
            i18n.tr("Book (*.json *.kepy);;All files (*)"),
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        """Open a book project in a new tab."""
        from epy_books._ui.tab import BookTab

        try:
            tab = BookTab(path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                i18n.tr("Open book"),
                i18n.tr("Could not open: {error}", error=exc),
            )
            return
        index = self.tabs.addTab(tab, tab.book.manifest.title)
        self.tabs.setCurrentIndex(index)
        self.statusBar().showMessage(str(path))

    def open_demo(self) -> None:
        """Open the writable copy of the bundled demo book."""
        self.open_path(demo_project_path(i18n.current_language()))

    def _validate_current(self) -> None:
        tab = self.tabs.currentWidget()
        if tab is not None and hasattr(tab, "validate"):
            tab.validate.click()

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
