import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import Header from "./comps/Header.jsx";
import Map from "./comps/Map.jsx";
import Results from "./comps/Result.jsx";
import './styles.css';
import Footer from './comps/Footer.jsx';
import { fetchAnalysis } from './api.js';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [location, setLocation] = useState(null);

  async function handleAnalyze() {
    if (!location) {
      setError("Draw your farm boundary on the map first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setData(await fetchAnalysis(location.lat, location.lng));
    } catch (err) {
      setData(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Header />

      <main className="main-layout">

        <section className="map-section">
          <Map onLocationChange={setLocation} />
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
          <input type="text" placeholder="Total cost" className="cost-inputs" />
          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={loading || !location}
          >
            {loading ? "Loading..." : "Analyze My Farm"}
          </button>
          {!location && (
            <p className="analyze-hint">Draw your farm boundary on the map to enable analysis.</p>
          )}
        </section>
      </main>
      <Results data={data} loading={loading} error={error} />
      <Footer />
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);