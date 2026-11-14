
import React from 'react';
import { createRoot } from 'react-dom/client';
import Header from "./comps/header.jsx";
import Map from "./comps/map.jsx";
import './styles.css';

function App() {
  return (
    <>
      <Header />

      <main className="main-layout">

        <section className="map-section">
          <Map />
        </section>

        <section className="farm-form">
          <h2>Farm Information</h2>
          <p>Enter your farm details to get started.</p>

          <div className="form-group">
            <label>Last Crop Planted</label>
            <select defaultValue="">
              <option value="" disabled>Select crop</option>
              <option>Wheat</option>
              <option>Corn</option>
              <option>Soybeans</option>
              <option>Cotton</option>
              <option>Other</option>
            </select>
          </div>

          <div className="form-group">
            <label>Water Source</label>
            <select defaultValue="">
              <option value="" disabled>Select water source</option>
              <option>Groundwater / Well</option>
              <option>Surface Water</option>
              <option>Rainwater</option>
              <option>Municipal Water</option>
              <option>Other</option>
            </select>
          </div>

          <button className="analyze-btn">
            Analyze My Farm
          </button>
        </section>

      </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
