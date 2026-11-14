import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Header from "./comps/header.jsx";
import Map from "./comps/map.jsx";
import './styles.css';

function App() {
  
  return (
    <>
    <Header />
    <main>
      <Map />
    </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
