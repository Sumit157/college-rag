"""Document parsers for PDF, DOCX, PPTX and TXT.

Every parser emits :class:`ParsedUnit` values that preserve the best
available source metadata: page number (when the format has pages) and the
active section heading.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Protocol

from app.ingestion.errors import CorruptDocumentError, EmptyDocumentError
from app.ingestion.sections import is_heading


@dataclass
class ParsedUnit:
    text: str
    page: int | None = None
    section: str | None = None


class DocumentParser(Protocol):
    extension: str

    def parse(self, data: bytes, filename: str) -> list[ParsedUnit]: ...


def _units_from_lines(
    lines: list[str],
    page: int | None,
) -> list[ParsedUnit]:
    """Group lines into section runs on a single page/document."""
    units: list[ParsedUnit] = []
    section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if text:
            units.append(ParsedUnit(text=text, page=page, section=section))
        buffer = []

    for raw in lines:
        line = raw.strip()
        if is_heading(line):
            flush()
            section = line.lstrip("#").strip()
            continue
        buffer.append(raw)
    flush()
    return units


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CorruptDocumentError("The text file could not be decoded.")


class TXTParser:
    extension = ".txt"

    def parse(self, data: bytes, filename: str) -> list[ParsedUnit]:
        text = _decode_text(data)
        lines = text.split("\n")
        units = _units_from_lines(lines, page=None)
        if not units and text.strip():
            units = [ParsedUnit(text=text.strip(), page=None, section=None)]
        if not units:
            raise EmptyDocumentError("The document does not contain any text.")
        return units


class PDFParser:
    extension = ".pdf"

    def parse(self, data: bytes, filename: str) -> list[ParsedUnit]:
        import pymupdf

        try:
            document = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise CorruptDocumentError("The PDF file could not be opened.") from exc

        units: list[ParsedUnit] = []
        try:
            if document.page_count == 0:
                raise EmptyDocumentError("The PDF does not contain any pages.")
            for index in range(document.page_count):
                page = document.load_page(index)
                text = page.get_text("text")
                page_units = _units_from_lines(text.split("\n"), page=index + 1)
                units.extend(page_units)
        finally:
            document.close()

        if not units:
            raise EmptyDocumentError(
                "The PDF does not contain extractable text (it may be a scanned document)."
            )
        return units


class DOCXParser:
    extension = ".docx"

    def parse(self, data: bytes, filename: str) -> list[ParsedUnit]:
        import docx

        try:
            document = docx.Document(io.BytesIO(data))
        except Exception as exc:
            raise CorruptDocumentError("The DOCX file could not be opened.") from exc

        lines: list[str] = []
        section: str | None = None
        units: list[ParsedUnit] = []
        buffer: list[str] = []

        def flush() -> None:
            nonlocal buffer
            text = "\n".join(buffer).strip()
            if text:
                units.append(ParsedUnit(text=text, page=None, section=section))
            buffer = []

        for block in document.iter_inner_content():
            style_name = ""
            if hasattr(block, "style") and block.style is not None:
                style_name = (block.style.name or "").lower()

            if hasattr(block, "rows"):
                for row in block.rows:
                    cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    line = " | ".join(c for c in cells if c)
                    if line:
                        buffer.append(line)
                continue

            paragraph_text = block.text.strip()
            if not paragraph_text:
                if buffer:
                    buffer.append("")
                continue

            is_heading_style = style_name.startswith("heading") or style_name == "title"
            if is_heading_style or is_heading(paragraph_text):
                flush()
                section = paragraph_text.lstrip("#").strip()
                buffer.append(paragraph_text)
            else:
                buffer.append(paragraph_text)
            lines.append(paragraph_text)

        flush()
        if not units and lines:
            units = [ParsedUnit(text="\n".join(lines).strip(), page=None, section=None)]
        if not units:
            raise EmptyDocumentError("The document does not contain any text.")
        return units


class PPTXParser:
    extension = ".pptx"

    def parse(self, data: bytes, filename: str) -> list[ParsedUnit]:
        import pptx

        try:
            presentation = pptx.Presentation(io.BytesIO(data))
        except Exception as exc:
            raise CorruptDocumentError("The PPTX file could not be opened.") from exc

        units: list[ParsedUnit] = []
        for index, slide in enumerate(presentation.slides, start=1):
            lines: list[str] = []
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in paragraph.runs).strip()
                    if line:
                        lines.append(line)
            text = "\n".join(lines).strip()
            if not text:
                continue
            title = None
            if slide.shapes.title is not None:
                title = (slide.shapes.title.text or "").strip() or None
            if title is None:
                title = lines[0] if is_heading(lines[0]) else None
            units.append(ParsedUnit(text=text, page=index, section=title))

        if not units:
            raise EmptyDocumentError("The presentation does not contain any text.")
        return units


_PARSERS: dict[str, DocumentParser] = {
    ".pdf": PDFParser(),
    ".docx": DOCXParser(),
    ".pptx": PPTXParser(),
    ".txt": TXTParser(),
}


def get_parser(extension: str) -> DocumentParser:
    try:
        return _PARSERS[extension]
    except KeyError:
        from app.ingestion.errors import UnsupportedFileTypeError

        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension}'. Supported types: PDF, DOCX, PPTX, TXT."
        ) from None
