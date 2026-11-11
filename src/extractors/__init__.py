"""extractors package — модуль извлечения данных из различных форматов файлов."""

from .pdf import extract_text_from_pdf
from .docx import extract_text_from_docx
from .xlsx import extract_text_from_xlsx
from .pptx import extract_text_from_pptx
from .text import extract_text_from_text

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_docx",
    "extract_text_from_xlsx",
    "extract_text_from_pptx",
    "extract_text_from_text",
]