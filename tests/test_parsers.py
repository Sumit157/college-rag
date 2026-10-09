"""Parser tests using generated PDF/DOCX/PPTX/TXT fixtures."""

import pytest

from app.ingestion.errors import CorruptDocumentError, EmptyDocumentError
from app.ingestion.parsers import DOCXParser, PDFParser, PPTXParser, TXTParser, get_parser

from tests.conftest import build_docx, build_pdf, build_pptx, build_txt


def test_registry_returns_parsers() -> None:
    assert isinstance(get_parser(".pdf"), PDFParser)
    assert isinstance(get_parser(".docx"), DOCXParser)
    assert isinstance(get_parser(".pptx"), PPTXParser)
    assert isinstance(get_parser(".txt"), TXTParser)


def test_txt_parser_sections_and_pages() -> None:
    units = TXTParser().parse(build_txt(), "notes.txt")
    assert units
    assert all(u.page is None for u in units)
    sections = [u.section for u in units]
    assert "1. Introduction" in sections
    assert "2. Paging" in sections
    joined = "\n".join(u.text for u in units)
    assert "Paging divides physical memory" in joined


def test_txt_parser_without_headings() -> None:
    units = TXTParser().parse(b"just some plain text\nsecond line", "a.txt")
    assert len(units) == 1
    assert units[0].section is None
    assert units[0].page is None


def test_txt_parser_empty_raises() -> None:
    with pytest.raises(EmptyDocumentError):
        TXTParser().parse(b"   \n \n", "a.txt")


def test_pdf_parser_pages() -> None:
    data = build_pdf(
        [
            "1. Introduction\nOperating systems manage resources.",
            "2. Paging\nPaging divides memory into frames.",
        ]
    )
    units = PDFParser().parse(data, "os.pdf")
    assert {u.page for u in units} == {1, 2}
    joined = "\n".join(u.text for u in units)
    assert "Operating systems manage resources." in joined
    assert "Paging divides memory into frames." in joined
    page2_sections = [u.section for u in units if u.page == 2]
    assert page2_sections and page2_sections[0] == "2. Paging"


def test_pdf_parser_corrupt_raises() -> None:
    with pytest.raises(CorruptDocumentError):
        PDFParser().parse(b"%PDF-1.4\nnot a real pdf body", "bad.pdf")


def test_pdf_parser_empty_pdf_raises() -> None:
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    with pytest.raises(EmptyDocumentError):
        PDFParser().parse(data, "empty.pdf")


def test_docx_parser_headings_and_tables() -> None:
    units = DOCXParser().parse(build_docx(), "os.docx")
    assert units
    sections = [u.section for u in units]
    assert "Operating Systems" in sections
    assert "Paging" in sections
    joined = "\n".join(u.text for u in units)
    assert "Processes and threads are fundamental OS concepts." in joined
    assert "Frame | A fixed-size block of physical memory" in joined


def test_docx_parser_corrupt_raises() -> None:
    with pytest.raises(CorruptDocumentError):
        DOCXParser().parse(b"not a docx at all", "bad.docx")


def test_pptx_parser_slides_and_titles() -> None:
    units = PPTXParser().parse(build_pptx(), "deck.pptx")
    assert len(units) == 2
    assert units[0].page == 1
    assert units[0].section == "Paging"
    assert units[1].page == 2
    assert units[1].section == "Segmentation"
    assert "fixed-size frames" in units[0].text


def test_pptx_parser_corrupt_raises() -> None:
    with pytest.raises(CorruptDocumentError):
        PPTXParser().parse(b"PK\x03\x04 broken", "bad.pptx")
