import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Header from "./comps/Header.jsx";
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
    <>
    <Header />
    <main>
      
    </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
