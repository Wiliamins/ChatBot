Zadanie projektowe – Webowy Chatbot z analizą dokumentów i CMS
Lekki widżet czatu (React + FastAPI), który odpowiada na pytania na podstawie wgranych plików (TXT/CSV/DOCX/PDF) oraz treści CMS (JSON), z użyciem Qdrant Cloud jako wektorowej bazy danych.
Włączony jest tryb dokładnego indeksowania KV — każda para Klucz: Wartość trafia do bazy jako osobny wektor → odpowiedzi są krótkie i precyzyjne (np. „delivery date” → 2026-02-15).
Zasada priorytetu: ostatnie źródło wygrywa (najpierw przeszukujemy ostatnio wgrany plik lub ostatni CMS).

Funkcjonalności

Osadzony widżet czatu (bubble UI), responsywny (desktop + mobile).

⬆Upload plików: TXT, CSV, DOCX, PDF (nie-skan).

Import CMS: wysyłka JSON, który jest spłaszczany do par Klucz:Wartość.

Wyszukiwanie semantyczne + dokładne KV: każda para indeksowana osobno, zwracane krótkie wartości (np. Aurora, Gdańsk, 24 hours).

Qdrant Cloud (URL + API Key), przechowywane metadane: source, source_type, file_type, q, a, q_norm, seq, text.

Bezpieczne aliasy (EN + podstawowe RU/PL) dla rozpoznawania popularnych pytań (name, delivery date, office, sla, email, …).

Priorytet ostatniego źródła: plik/CMS wgrany jako ostatni jest przeszukiwany w pierwszej kolejności.
Architektura

Frontend: React (widżet czatu, prosty, dostępny UI).

Backend: FastAPI (CORS, endpointy /upload, /cms, /query).

Embeddings: sentence-transformers/all-MiniLM-L6-v2 (384 wym.).

Wektorowa baza: Qdrant Cloud (połączenie zdalne: URL + API Key).

Parser treści: document_parser.py:

Key: Value

Key | Value (wiersze CSV)

FAQ q. ... a. ...

Bloki po nagłówku (Overview: + kolejne linie)

Indeksowanie: każda para KV osobną kropką w Qdrant + seq (kolejność w pliku; przy duplikatach bierzemy ostatnią wartość).

Struktura projektu
project/
├─ frontend/
│  ├─ public/
│  │  └─ index.html
│  └─ src/
│     ├─ App.js
│     ├─ Chatbot.js
│     └─ styles.css
└─ backend/
   ├─ app.py
   ├─ qdrant_utils.py
   ├─ embeddings.py
   ├─ document_parser.py
   └─ requirements.txt

API (backend)
POST /upload

Opis: wgrywa i indeksuje plik.

Body (form-data): file (TXT/CSV/DOCX/PDF)

Odpowiedź: { "message": "File processed and stored", "pairs": <ile_par> }

POST /cms

Opis: przyjmuje JSON z CMS; spłaszcza do par i indeksuje.

Body (JSON): dowolny zagnieżdżony obiekt.

Odpowiedź: { "message": "CMS content processed and stored", "pairs": <ile_par> }

POST /query

Opis: zadaje pytanie.

Body (JSON): { "query": "delivery date" }

Odpowiedź: { "answer": "<krótka_wartość>", "source": "<źródło>" } lub komunikat o braku.

Pliki testowe i scenariusze testów:
file: test_chatbott.csv
name → ChatPilot

project codename → ChatPilot

delivery date / date / deadline → 2025-11-30

office / office city / city → Warsaw

headcount / team size → 3

ceo? → Viliam

file: test_chatbot/txt
project name → Mark2

delivery date / date → 2025-10-10

office / office city → Warsaw

file: test_chatbot.doxc
developer → Viliamin Stepushenkov

project → ChatBot

main stack → Python, FastAPI, React

file: testchatbot_PDF
name / project codename → ChatPilot

delivery date / date / deadline → 2026-02-15

office / office city / city → Gdańsk

headcount / team size → 6

ceo? → Martin Nowak

support hours / working hours → Mon–Sat 08:00–20:00 CET

contact email? / email → support@chatpilot.dev

what's the sla? / sla → 12 hours

tech stack / stack → React, FastAPI, Qdrant, Sentence-Transformers

overview /  Overview

Jak wybierana jest odpowiedź

Zapytanie jest mapowane na klucz kanoniczny (np. date → delivery date, office → office city).

Najpierw szukamy dokładnego dopasowania klucza w ostatnim źródle (q_norm == target_norm + source == LATEST_SOURCE).

Jeśli nie ma dopasowania w ostatnim źródle — szukamy globalnie.

Gdy w ramach jednego źródła dany klucz występuje wiele razy — zwracamy ostatnią parę (max(seq)).

Jeśli klucza nie ma nigdzie — zwracamy No relevant information found.

Jeśli nie da się zmapować klucza, używamy semantycznego wyszukiwania i próbujemy zwrócić wartość z najtrafniejszej pary.

Rozwiązywanie problemów (Troubleshooting)

python-multipart wymagane przy /upload:
pip install python-multipart

Błąd połączenia z Qdrant (Connection refused):

sprawdź QDRANT_URL i QDRANT_API_KEY,

czy klaster działa i nie blokuje połączeń,

firewall / proxy.

CORS / przeglądarka blokuje zapytania:
uzupełnij allow_origins w app.py o właściwy origin frontendu.

Zwraca No relevant information found:

czy pytasz istniejącym kluczem (project codename, delivery date, office city, headcount, sla, contact email, tech stack, overview, developer, project name)?

czy ostatnie źródło zawiera ten klucz?

PDF to skan (obraz) — brak OCR: parser nie wyciągnie tekstu (patrz Ograniczenia).

Ograniczenia

Brak OCR (skany/obrazy nie są parsowane).

XLSX/HTML/Markdown nie są wspierane domyślnie.

Aliasów jest celowo niewiele (EN), aby unikać błędnych dopasowań — łatwo dodać własne w SAFE_MAP.