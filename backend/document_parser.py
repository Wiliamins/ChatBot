import os
import re
import csv
from io import StringIO
from typing import List, Dict, Any

from docx import Document as DocxDocument
from pdfminer.high_level import extract_text

# ----- Алиасы и нормализация ключей -----

ALIAS_MAP = {
    # имя проекта
    "name": "project name",
    "project name": "project name",
    "name of the project": "project name",
    "название": "project name",
    "название проекта": "project name",
    "nazwa": "project name",
    "nazwa projektu": "project name",

    # кодовое имя
    "codename": "project codename",
    "code name": "project codename",
    "project codename": "project codename",
    "кодовое имя": "project codename",
    "kryptonim": "project codename",

    # даты
    "date": "delivery date",
    "deadline": "delivery date",
    "delivery date": "delivery date",

    # офис
    "office": "office city",
    "office city": "office city",
    "city": "office city",
    "город": "office city",
    "miasto": "office city",

    # команды/роли
    "headcount": "headcount",
    "team size": "headcount",
    "employees": "headcount",
    "ceo": "ceo",
    "developer": "developer",

    # поддержка/контакты
    "support hours": "support hours",
    "working hours": "support hours",
    "email": "contact email",
    "contact email": "contact email",
    "sla": "sla",

    # стеки
    "tech stack": "tech stack",
    "stack": "tech stack",
    "main stack": "main stack",

    # прочее
    "project": "project",
    "overview": "overview",
}

def _strip(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

def normalize_key(k: str) -> str:
    """
    jr-komentarz (PL): normalizuję klucze do małych liter, usuwam znaki interpunkcyjne i mapuję aliasy,
    żeby pytania użytkownika (np. 'name', 'project name') trafiały w jeden kanoniczny klucz.
    """
    if not isinstance(k, str):
        return ""
    s = k.strip().lower()
    s = s.replace("–", "-")
    s = s.replace(":", " ").replace("?", " ").replace(".", " ").replace("-", " ")
    s = re.sub(r"[\s/_\-]+", " ", s).strip()
    return ALIAS_MAP.get(s, s)

def _add_pair(pairs: List[Dict[str, Any]], raw_key: str, value: str):
    raw_key = _strip(raw_key)
    value = _strip(value)
    if not raw_key or value is None or value == "":
        return
    q_norm = normalize_key(raw_key)
    pairs.append({
        "q": raw_key,
        "q_norm": q_norm,
        "a": value,
        "text": f"{raw_key}: {value}",
    })

# ----- Регексы -----
KV_COLON = re.compile(r"^\s*([^:\n]{1,80}?)\s*:\s*(.+?)\s*$")
KV_PIPE  = re.compile(r"^\s*([^|\n]{1,80}?)\s*\|\s*(.+?)\s*$")
FAQ_Q    = re.compile(r"^\s*q[\.\:\-]\s*(.+?)\s*$", re.IGNORECASE)
FAQ_A    = re.compile(r"^\s*a[\.\:\-]\s*(.+?)\s*$", re.IGNORECASE)

def _extract_overview_pairs(lines: List[str]) -> List[Dict[str, Any]]:
    """
    jr-komentarz (PL): wcześniej przerywałem Overview na 'Key: Value',
    przez co uciekał dalszy tekst; teraz zbieram aż do 'nagłówka-sekcji' typu 'Something:'
    lub FAQ (q./a.). Puste linie zachowuję (to akapity).
    """
    pairs: List[Dict[str, Any]] = []
    i = 0
    NEXT_HDR = re.compile(r"^\s*[A-Za-z][\w \-/]{1,60}:\s*$")  # tytuł następnej sekcji

    while i < len(lines):
        raw = lines[i]
        ln = raw.strip()
        if ln.lower().startswith("overview"):
            rest = ln[len("overview"):].lstrip(" \t:-—–")
            chunk: List[str] = []
            if rest:
                chunk.append(rest)

            i += 1
            while i < len(lines):
                cur = lines[i]
                # стоп-условия: явный новый заголовок секции или FAQ
                if FAQ_Q.match(cur) or FAQ_A.match(cur) or NEXT_HDR.match(cur):
                    break
                # иначе — добавляем строку как есть (включая пустые, чтобы не терять абзацы)
                chunk.append(cur)
                i += 1

            text = "\n".join(s.rstrip() for s in chunk)
            if text.strip():
                _add_pair(pairs, "Overview", text.strip())
        else:
            i += 1
    return pairs

def extract_pairs_from_text(text: str) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    if not text:
        return pairs

    text = text.replace("\xa0", " ")
    lines = [l.rstrip() for l in text.splitlines()]

    # 1) Overview (многоабзацный)
    pairs.extend(_extract_overview_pairs(lines))

    # 2) Простые пары "Key: Value" и "Key | Value"
    for ln in lines:
        m = KV_COLON.match(ln)
        if m:
            raw_k = m.group(1)
            # ВАЖНО: пропускаем Overview в этом проходе, чтобы не делать дубль
            if normalize_key(raw_k) == "overview":
                continue
            _add_pair(pairs, raw_k, m.group(2))
            continue
        m = KV_PIPE.match(ln)
        if m:
            _add_pair(pairs, m.group(1), m.group(2))
            continue

    # 3) FAQ "q. ... / a. ..."
    q_buffer = None
    for ln in lines:
        mq = FAQ_Q.match(ln)
        ma = FAQ_A.match(ln)
        if mq:
            q_buffer = mq.group(1)
            continue
        if ma and q_buffer:
            _add_pair(pairs, q_buffer, ma.group(1))
            q_buffer = None

    return pairs

# ----- Чтение файлов -----
def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _read_docx(path: str) -> str:
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs)

def _read_pdf(path: str) -> str:
    txt = extract_text(path) or ""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", txt)

def _read_csv(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    for delim in ["|", ";", ",", "\t"]:
        try:
            f = StringIO(data)
            reader = csv.reader(f, delimiter=delim)
            rows = list(reader)
            if rows and len(rows[0]) >= 2:
                out = []
                for r in rows:
                    if len(r) >= 2 and r[0].strip() and r[1].strip():
                        out.append(f"{r[0].strip()} | {r[1].strip()}")
                if out:
                    return "\n".join(out)
        except Exception:
            pass
    return data

def parse_file(path: str, filename: str | None = None) -> List[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        text = _read_txt(path)
    elif ext == ".docx":
        text = _read_docx(path)
    elif ext == ".pdf":
        text = _read_pdf(path)
    elif ext == ".csv":
        text = _read_csv(path)
    else:
        text = _read_txt(path)
    return extract_pairs_from_text(text)

# ----- CMS JSON с поддержкой {q, a} -----
def _flatten_json(obj: Any, parent_key: str = "") -> Dict[str, Any]:
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}.{k}" if parent_key else str(k)
            items.update(_flatten_json(v, new_key))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            new_key = f"{parent_key}.{idx}" if parent_key else str(idx)
            items.update(_flatten_json(v, new_key))
    else:
        items[parent_key] = obj
    return items

def _collect_qa_pairs(node: Any, out_pairs: List[Dict[str, Any]]):
    if isinstance(node, dict):
        if "q" in node and "a" in node:
            q_val = node.get("q")
            a_val = node.get("a")
            if isinstance(q_val, (str, int, float)) and isinstance(a_val, (str, int, float)):
                _add_pair(out_pairs, str(q_val), str(a_val))
        for v in node.values():
            _collect_qa_pairs(v, out_pairs)
    elif isinstance(node, list):
        for item in node:
            _collect_qa_pairs(item, out_pairs)

def parse_cms_content(cms: dict) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    _collect_qa_pairs(cms, pairs)

    flat = _flatten_json(cms)
    for dotted_key, value in flat.items():
        if value is None:
            continue
        # не дублируем элементы массивов FAQ
        if re.search(r"\.\d+\.(q|a)$", dotted_key, flags=re.IGNORECASE):
            continue
        val = str(value).strip()
        if val == "":
            continue
        display_key = dotted_key.replace(".", " ")
        _add_pair(pairs, display_key, val)
    return pairs
