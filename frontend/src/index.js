// Ten plik jest wejściem aplikacji React.
// Tworzę "root" i renderuję komponent App do <div id="root"> z index.html

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Pobieram element z DOM, gdzie React się zamontuje
const root = ReactDOM.createRoot(document.getElementById('root'));

// Renderuję aplikację w trybie StrictMode (pomaga wychwycić błędy w dev)
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
