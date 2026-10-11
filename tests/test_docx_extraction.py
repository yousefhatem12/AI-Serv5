from __future__ import annotations
from pathlib import Path
from src.cv_extractor.document_loader import DocumentLoader


def test_docx_extraction():
    loader = DocumentLoader()
    docx_path = Path(__file__).parent / "samples" / "yousef_hatem_cv.docx"
    assert docx_path.exists(), "Sample docx file missing"

    extracted_text, doc_format, doc_links = loader.load_text(str(docx_path))
    assert doc_format == "docx"
    assert isinstance(extracted_text, str)
    assert len(extracted_text.strip()) > 0
    assert isinstance(doc_links, list)


def test_docs_and_doc_extraction_with_renamed_docx(tmp_path):
    """Ensure .doc and .docs extensions wrapping docx format extract seamlessly."""
    loader = DocumentLoader()
    sample_docx = Path(__file__).parent / "samples" / "yousef_hatem_cv.docx"
    assert sample_docx.exists()

    content = sample_docx.read_bytes()

    for ext in [".doc", ".docs"]:
        target_file = tmp_path / f"test_cv{ext}"
        target_file.write_bytes(content)

        extracted_text, doc_format, doc_links = loader.load_text(str(target_file))
        assert doc_format == "doc"
        assert len(extracted_text.strip()) > 0
        assert "yousef" in extracted_text.lower() or "hatem" in extracted_text.lower()
        assert isinstance(doc_links, list)


def test_doc_extraction_with_rtf_format(tmp_path):
    """Ensure .doc and .docs files containing RTF text extract correctly."""
    loader = DocumentLoader()
    rtf_content = rb"{\rtf1\ansi\deff0 {\fonttbl {\f0 Courier;}}\f0\fs24 Candidate: Sarah Connor\par Role: Senior Software Engineer\par Skills: Python, FastAPI\par Contact: https://example.com/profile}"

    for ext in [".doc", ".docs"]:
        target_file = tmp_path / f"resume{ext}"
        target_file.write_bytes(rtf_content)

        extracted_text, doc_format, doc_links = loader.load_text(str(target_file))
        assert doc_format == "doc"
        assert "Sarah Connor" in extracted_text
        assert "Senior Software Engineer" in extracted_text
        assert "https://example.com/profile" in doc_links


