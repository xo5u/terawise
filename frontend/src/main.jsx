import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

function App() {
  const [connection, setConnection] = useState({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setConnection({ status: 'loading' });

    async function checkConnection() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal });
        if (!response.ok) throw new Error('API request failed');
        const data = await response.json();
        if (data.status !== 'ok') throw new Error('API is unavailable');
        setConnection({ status: 'connected', message: data.message });
      } catch (error) {
        if (!controller.signal.aborted) setConnection({ status: 'error' });
      }
    }

    checkConnection();
    return () => controller.abort();
  }, [attempt]);

  return (
    <main>
      <p className="eyebrow">TERAWISE</p>
      <h1>Ready to build.</h1>
      <p>Your React frontend and FastAPI backend are set up.</p>
      <section aria-label="API connection" aria-live="polite">
        <h2>Backend connection</h2>
        <p>
          {connection.status === 'loading' && 'Connecting to the API…'}
          {connection.status === 'connected' && connection.message}
          {connection.status === 'error' && 'Unable to reach the API. Start the backend, then try again.'}
        </p>
        <button disabled={connection.status === 'loading'} onClick={() => setAttempt((value) => value + 1)}>
          Check connection
        </button>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
