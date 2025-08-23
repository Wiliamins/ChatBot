// src/Chatbot.js
// ------------------------------------------------------------
// Prosty widżet czatu (React) do rozmowy z backendem FastAPI.
// Funkcje w skrócie:
//  - wysyłanie pytań do /query
//  - wysyłanie plików do /upload (multipart/form-data)
//  - wysyłanie JSON do /cms (symulacja danych z CMS)
//  - wiadomości w kolumnie: bot po lewej, user po prawej
//  - przyciski w jednym stylu (klasy .btn i .btn-primary)
//  - preferowanie odpowiedzi z ostatnio wgranego pliku (prefer_source)
// Uwaga: style są w pliku styles.css (klasy .chatbot-* itd.).
// ------------------------------------------------------------

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './styles.css';

// Adres API - jak jest zmienna REACT_APP_API_URL, to użyję jej,
// jak nie ma, to biorę domyślnie localhost
const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Chatbot({ docked = false }) {
  // Tutaj trzymam wszystkie stany potrzebne do działania czatu
  const [messages, setMessages]   = useState([]);     // lista wiadomości (obiekty z text i sender)
  const [input, setInput]         = useState('');     // tekst z inputa
  const [loading, setLoading]     = useState(false);  // czy czekamy na odpowiedź z backendu
  const [fileName, setFileName]   = useState('');     // nazwa ostatnio wybranego pliku (do podglądu)
  const [preferSource, setPreferSource] = useState(null); // preferowany "source" (nazwa pliku)
  const [cmsJSON, setCmsJSON]     = useState(
    // Domyślny JSON, żeby można było łatwo kliknąć "Send CMS" i testować
    '{\n  "faq": [\n    {"q":"Project name","a":"ChatBotVS"},\n    {"q":"Budget","a":"2.5M"}\n  ]\n}'
  );

  // Referencja do ostatniego elementu listy (do przewijania na dół)
  const messagesEndRef = useRef(null);

  // Kiedy zmieniają się messages lub loading, to scrolluję na dół (fajniej się używa)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Funkcja do wysyłania wiadomości tekstowej do /query
  async function sendMessage() {
    const text = input.trim(); // usuwam spacje z obu stron
    if (!text || loading) return; // nie wysyłam pustych i nie spamuję w trakcie ładowania

    // Najpierw dodaję wiadomość użytkownika do UI (tzw. optimistic update)
    setMessages(prev => [...prev, { text, sender: 'user' }]);
    setInput('');     // czyszczę pole
    setLoading(true); // ustawiam stan ładowania

    try {
      // Wysyłam POST do backendu. Daję prefer_source, żeby backend spróbował
      // najpierw użyć danych z ostatnio wgranego pliku (jeśli jest ustawiony).
      const { data } = await axios.post(`${API}/query`, {
        query: text,
        prefer_source: preferSource || null
        // prefer_source_type: 'file'  // (opcjonalnie, jak zaimplementowane w backendzie)
      });

      // Jak backend zwróci źródło (np. nazwa pliku albo "cms"), to pokażę je pod odpowiedzią
      const meta = data?.source ? `\n\n— source: ${data.source}` : '';

      // Dodaję wiadomość bota do listy
      setMessages(prev => [
        ...prev,
        { text: (data?.answer ?? 'No answer') + meta, sender: 'bot' }
      ]);
    } catch (e) {
      // Jak coś poszło nie tak (np. backend nie działa), to wyświetlam prosty błąd
      setMessages(prev => [...prev, { text: 'Error: Could not get response', sender: 'bot' }]);
    } finally {
      setLoading(false); // kończę ładowanie (żeby znowu można było wysyłać)
    }
  }

  // Funkcja do uploadu pliku. Po udanym uploadzie ustawiam preferSource na nazwę pliku,
  // żeby kolejne pytania celowały w świeżo dodane dane
  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);     // pokazuję nazwę pliku w UI (taka informacja)
    setPreferSource(file.name); // preferuj odpowiedzi z tego pliku

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // Jak się udało, to wrzucam komunikat do czatu
      setMessages(prev => [...prev, { text: `Uploaded: ${file.name}`, sender: 'bot' }]);
    } catch (e) {
      setMessages(prev => [...prev, { text: 'Error uploading file', sender: 'bot' }]);
    } finally {
      setLoading(false);
      e.target.value = ''; // resetuję input, żeby można było wybrać ten sam plik ponownie
    }
  }

  // Funkcja do wysyłania JSON-a do /cms (symulacja danych z systemu CMS)
  async function sendCMS() {
    let parsed;
    // Najpierw sprawdzam, czy JSON jest poprawny (żeby nie wywrócić frontu)
    try {
      parsed = JSON.parse(cmsJSON);
    } catch {
      setMessages(prev => [...prev, { text: 'CMS JSON is invalid', sender: 'bot' }]);
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/cms`, { content: parsed });
      setMessages(prev => [...prev, { text: 'CMS content stored', sender: 'bot' }]);
    } catch (e) {
      setMessages(prev => [...prev, { text: 'Error storing CMS', sender: 'bot' }]);
    } finally {
      setLoading(false);
    }
  }

  // Obsługa Entera: Enter wysyła wiadomość,
  // a Shift+Enter pozwala dodać nową linię (gdyby kiedyś było textarea)
  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // Render UI
  return (
    <div className={`chatbot-container ${docked ? 'docked' : ''}`}>
      {/* Tutaj wyświetlam wszystkie wiadomości (u góry najstarsze, na dole najnowsze) */}
      <div className="chatbot-messages">
        {messages.map((m, i) => (
          // Daję key = index, bo tutaj sekwencja jest prosta i wystarczy
          <div key={i} className={`message ${m.sender}`}>{m.text}</div>
        ))}

        {/* W trakcie requestu pokazuję prosty wskaźnik pisania (3 kropki) */}
        {loading && <div className="typing"><span></span><span></span><span></span></div>}

        {/* Ten element jest kotwicą do autoscrolla (scrollIntoView) */}
        <div ref={messagesEndRef} />
      </div>

      {/* Panel z inputem i przyciskami */}
      <div className="chatbot-input">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask something…"
        />

        {/* Przycisk wysyłania wiadomości. Disabled jak nie ma tekstu albo trwa ładowanie */}
        <button
          className="btn btn-primary"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          Send
        </button>

        {/* Ukryty natywny input do pliku i label jako ładny przycisk */}
        <input
          id="file-upload"
          type="file"
          className="visually-hidden"
          onChange={handleFileUpload}
          accept=".txt,.csv,.docx,.pdf"
        />
        <label className="btn" htmlFor="file-upload" role="button" tabIndex={0}>
          Choose file
        </label>

        {/* Dodatkowo pokazuję nazwę wybranego pliku (jak jest) */}
        {fileName && <span className="file-name">{fileName}</span>}
      </div>

      {/* Dodatkowa sekcja do wklejenia CMS JSON i wysłania na backend */}
      <details style={{ padding: '10px 10px 12px', borderTop: '1px solid rgba(255,255,255,.06)' }}>
        <summary style={{ cursor: 'pointer' }}>Simulate CMS input</summary>
        <textarea
          value={cmsJSON}
          onChange={e => setCmsJSON(e.target.value)}
          style={{ width: '100%', height: 120, marginTop: 8, borderRadius: 8, padding: 10 }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
          {/* Czyszczenie pola JSON (taki reset) */}
          <button className="btn" onClick={() => setCmsJSON('')}>Clear</button>
          {/* Wysyłka JSON do backendu */}
          <button className="btn btn-primary" onClick={sendCMS} disabled={loading}>Send CMS</button>
        </div>
      </details>
    </div>
  );
}
