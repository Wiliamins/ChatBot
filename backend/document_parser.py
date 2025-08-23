# document_parser.py
# ------------------------------------------------------------
# Junior (PL): Parser treści z plików i generator par Key:Value.
#  - Obsługuję:
#     * "Key: Value" (w tym nagłówki "Key:" + blok kolejnych linii)
#     * CSV-linie "Key | Value" (pomijam nagłówek "Question | Answer")
#     * FAQ q./a.
#  - Zwracam pary z polem "text" i "seq" (kolejność w pliku).
# ------------------------------------------------------------

import re
import csv
from io import StringIO
from typing import Any, Iterable, Dict, List
from pdfminer.high_level import extract_text as pdf_extract
from docx import Document

_KV_LINE = re.compile(r"^\s*([A-Za-z][\w\s\-/&]+?)\s*:\s*(.*)$", re.IGNORECASE)
FAQ_QA   = re.compile(
    r"(?:^|[\.\n>\-]\s*)q[\.:\)]?\s*(?P<q>[^.\n:]+?)\s*(?:[>\.\n]\s*)a[\.:\)]?\s*(?P<a>[^.\n]+)",
    re.IGNORECASE
)

def parse_file(path: str) -> str:
    ext = (path.split(".")[-1] or "").lower()
    if ext == "pdf":
        return (pdf_extract(path) or "").strip()
    if ext == "docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    if ext == "csv":
        out: List[str] = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        rdr = csv.reader(StringIO(txt))
        for row in rdr:
            if row:
                out.append(" | ".join(row))
        return "\n".join(out).strip()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()

def _yield_kv(q: str, a: str, seq: int) -> Dict[str, Any]:
    q = q.strip()
    a = a.strip()
    return {"q": q, "a": a, "text": f"{q}: {a}", "seq": seq}

def iter_kv_pairs_from_text(text: str) -> Iterable[Dict[str, Any]]:
    """
    Junior (PL): Wyciągam pary z całego tekstu.
      - FAQ q./a.
      - "Key: Value"
      - "Key:" + blok (zbieram kolejne linie aż do pustej linii lub następnego klucza)
      - CSV "Key | Value"
    """
    seq = 0
    T = text or ""

    # a) FAQ q./a.
    for m in FAQ_QA.finditer(T):
        q = m.group("q").strip(" .:")
        a = m.group("a").strip(" .:")
        if q and a:
            yield _yield_kv(q, a, seq); seq += 1

    # b) Linia po linii z obsługą bloków
    lines = (T.splitlines() if T else [])
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = _KV_LINE.match(ln)
        if not m:
            i += 1
            continue

        key = m.group(1).strip()
        rest = (m.group(2) or "").strip()

        if rest:  # zwykłe "Key: Value"
            yield _yield_kv(key, rest, seq); seq += 1
            i += 1
            continue

        # "Key:" + blok — zbieram kolejne linie do blanku lub następnego key-colon
        block: List[str] = []
        i += 1
        while i < len(lines):
            ln2 = lines[i]
            if not ln2.strip():
                # pusta linia kończy blok
                i += 1
                break
            if _KV_LINE.match(ln2):
                # kolejny klucz — kończę blok (nie konsumuję ln2 tutaj)
                break
            block.append(ln2.strip())
            i += 1
        value = " ".join(block).strip()
        if value:
            yield _yield_kv(key, value, seq); seq += 1

    # c) CSV-like: "Key | Value" (pomijam nagłówek)
    for ln in (T.splitlines() if T else []):
        if "|" not in ln:
            continue
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) != 2 or not all(parts):
            continue
        k, v = parts
        if k.lower() == "question" and v.lower() == "answer":
            continue
        yield _yield_kv(k, v, seq); seq += 1

def _fmt_key(k: str) -> str:
    s = str(k).replace("_", " ").strip()
    return s[:1].upper() + s[1:]

def iter_json_flat_kv(obj: Any, prefix: str = "", seq_start: int = 0) -> Iterable[Dict[str, Any]]:
    """
    Junior (PL): Spłaszczam JSON do par "ścieżka > klucz": wartość
    i nadaję kolejne seq, żeby mieć jednoznaczny porządek.
    """
    seq = seq_start

    def walk(x: Any, pfx: str):
        nonlocal seq
        if isinstance(x, dict):
            for k, v in x.items():
                key = _fmt_key(k) if not pfx else f"{pfx} > {_fmt_key(k)}"
                if isinstance(v, (str, int, float, bool)) and str(v).strip():
                    yield _yield_kv(key, str(v), seq); seq += 1
                else:
                    for it in walk(v, key):
                        yield it
        elif isinstance(x, list):
            for i, it in enumerate(x):
                key = f"{pfx} > {i}" if pfx else str(i)
                for it2 in walk(it, key):
                    yield it2

    yield from walk(obj, prefix)
