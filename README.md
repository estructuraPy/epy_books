# epy_books

Book authoring, editorial design and publication for the ePy suite.

`epy_books` is the sibling of `epy_reports`, `epy_slides` and `epy_papers`:

- one public authoring API: `Book`;
- configuration in `.epyson` under `src/epy_books/_config`;
- user input in `.json`;
- project state in `.kepy` with `minigit`;
- portable snapshots in `.zepy`;
- Studio integration through `epy_studio_connect`.

## Public API

```python
from epy_books import Book, available_designs, available_profiles

book = Book.from_file("coordinacion/libro.json")
book.validate("et_submission")
book.to_pdf("libro.pdf", design="aec_ingenieria")
book.to_epub("libro.epub", design="aec_ingenieria")
book.to_manuscript("manuscrito.docx")
```

Rendering is delegated to `epy_docs` through the suite bridge. Without
`epy_docs`, the authoring and validation API remains available.

## First release scope

- import the three pilot books from their existing `libro.json`;
- store documents, versions and attachments in `kepy`;
- `minigit` history with commits, diffs and restore;
- `zepy` pack, verify and unpack;
- AEC design family first, then the remaining sectors;
- Word manuscript for the Editorial Tecnologica del TEC;
- Studio registration from the first version.

PDF, DOCX, EPUB and the ET manuscript are implemented in this baseline.
Advanced cover design, automatic conceptual indexing and the full preview
surface remain the next milestones.

## Development

```bash
python -m pytest
python -m ruff check src tests
```
