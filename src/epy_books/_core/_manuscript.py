"""Apply the Editorial Tecnologica manuscript format to a DOCX."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def format_manuscript(path: str | Path) -> Path:
    """Set Arial 12, 1.5 spacing and 3 cm margins in a DOCX."""
    target = Path(path)
    document = Document(target)
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    for style_name in (
        "Body Text",
        "List Bullet",
        "List Number",
        "Quote",
        "Heading 1",
        "Heading 2",
        "Heading 3",
        "Heading 4",
        "Title",
        "Subtitle",
    ):
        if style_name in document.styles:
            style = document.styles[style_name]
            style.font.name = "Arial"
            if style_name != "Title":
                style.font.size = Pt(12)
            style.paragraph_format.line_spacing = 1.5
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            if run.font.name in (None, "Times New Roman", "Calibri"):
                run.font.name = "Arial"
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if run.font.name in (
                            None,
                            "Times New Roman",
                            "Calibri",
                        ):
                            run.font.name = "Arial"
                            run.font.size = Pt(12)
    for section in document.sections:
        section.page_width = Cm(21.59)
        section.page_height = Cm(27.94)
        section.left_margin = Cm(3)
        section.right_margin = Cm(3)
        section.top_margin = Cm(3)
        section.bottom_margin = Cm(3)
    settings = document.settings.element
    update = settings.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}updateFields"
    )
    if update is None:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)
    document.save(target)
    return target
