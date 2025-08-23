
// Tutaj dodaję nagłówek i główną sekcję z czatem.

import React from 'react';
import Chatbot from './Chatbot';
import './styles.css';

export default function App() {
  return (
    <div className="page">
      {/* Nagłówek na środku */}
      <header className="header">
        <h1>Welcome to the Chatbot Demo</h1>
        <p className="sub">Ask about your docs or CMS data</p>
      </header>

      <main className="main">
        {/*
          Przekazuję prop "docked", żeby panel wpisywania
          był przypięty na dole.
        */}
        <Chatbot docked />
      </main>

      <footer className="site-footer">
         Created by VS
      </footer>
    </div>
  );
}
