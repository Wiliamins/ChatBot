# backend/document_parser.py
import os
import csv
from io import StringIO
from typing import Dict, Any

from pdfminer.high_level import extract_text
from docx import Document

def _read_text_file(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    # пробуем utf-8, потом cp1251/cp1250
    for enc in ("utf-8", "cp1251", "cp1250", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")

def _read_csv_file(path: str) -> str:
    # читаем CSV стандартной библиотекой
    with open(path, "r", encoding="utf-8", newline="") as f:
        sample = f.read()
    f = StringIO(sample)
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
    except Exception:
        dialect = csv.excel
    f.seek(0)

    reader = csv.reader(f, dialect)
    rows = list(reader)
    if not rows:
        return ""

    # Если явные колонки Question/Answer — формируем удобный вид
    header = [h.strip().lower() for h in rows[0]]
    body = rows[1:] if len(rows) > 1 else []

    if "question" in header and "answer" in header:
        qi = header.index("question")
        ai = header.index("answer")
        lines = []
        for r in body:
            q = r[qi] if qi < len(r) else ""
            a = r[ai] if ai < len(r) else ""
            if q or a:
                lines.append(f"Question | Answer\n{q} | {a}")
        return "\n".join(lines)

    # Иначе просто склеиваем строки «v1 | v2 | v3»
    lines = [" | ".join([c.strip() for c in r]) for r in rows if any(c.strip() for c in r)]
    return "\n".join(lines)

def _read_docx_file(path: str) -> str:
    doc = Document(path)
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paras)

def _read_pdf_file(path: str) -> str:
    try:
        txt = extract_text(path) or ""
        return txt.strip()
    except Exception:
        return ""

def parse_file(path: str) -> str:
    """
    Универсальный парсер файлов по расширению -> текст.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        return _read_text_file(path)
    if ext == ".csv":
        return _read_csv_file(path)
    if ext == ".docx":
        return _read_docx_file(path)
    if ext == ".pdf":
        return _read_pdf_file(path)

    # по умолчанию пытаемся как текст
    return _read_text_file(path)

def parse_cms_content(content: Dict[str, Any]) -> str:
    """
    Преобразование CMS JSON в линейный текст.
    Специальный кейс для FAQ [{q,a}, ...], остальное — простой флаттен.
    """
    if not content:
        return ""

    if isinstance(content, dict) and "faq" in content and isinstance(content["faq"], list):
        lines = []
        for item in content["faq"]:
            q = str(item.get("q", "")).strip()
            a = str(item.get("a", "")).strip()
            if q:
                lines.append(f"Q: {q}")
            if a:
                lines.append(f"A: {a}")
        return "\n".join(lines)

    # общий флаттен словаря/массива
    def _flatten(obj, prefix=""):
        parts = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}{k}"
                parts.extend(_flatten(v, key + "."))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                key = f"{prefix}{i}"
                parts.extend(_flatten(v, key + "."))
        else:
            parts.append(f"{prefix[:-1]}: {obj}")
        return parts

    return "\n".join(_flatten(content))
