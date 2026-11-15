import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Header from "./comps/Header.jsx";
import Map from "./comps/Map.jsx";
import Results from "./comps/Result.jsx";
import './styles.css';
import Footer from './comps/Footer.jsx';
import { fetchCrops, fetchHistory, fetchRecommendation, recordPlanting } from './api.js';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [location, setLocation] = useState(null);

  const [crops, setCrops] = useState([]);
  const [lastCropId, setLastCropId] = useState("");
  const [tankWater, setTankWater] = useState("");
  const [plantingDate, setPlantingDate] = useState(today());
  const [history, setHistory] = useState([]);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [savingCropId, setSavingCropId] = useState(null);
  const [savedPlantings, setSavedPlantings] = useState([]);
  const [saveMessage, setSaveMessage] = useState(null);

  useEffect(() => {
    fetchCrops().then(setCrops).catch((err) => setError(err.message));
    let active = true;
    fetchHistory().then((rows) => {
      if (active) setHistory((previous) => {
        const byId = new Map(rows.map((row) => [row.id, row]));
        for (const row of previous) byId.set(row.id, row);
        return [...byId.values()].sort((a, b) => b.planting_date.localeCompare(a.planting_date));
      });
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  // Results belong to the farm they were calculated for, so redrawing the
  // boundary drops them rather than leaving them next to a different field.
  function handleLocationChange(next) {
    setLocation(next);
    setData(null);
    setError(null);
  }

  async function handleAnalyze() {
    if (!location) {
      setError("Draw your farm boundary on the map first.");
      return;
    }
    if (tankWater === "" || Number(tankWater) < 0) {
      setError("Enter the amount of water available in the tank, in litres.");
      return;
    }

    setLoading(true);
    setError(null);
    // Clear the previous run so stale recommendations are not left on screen
    // while the new one is still being calculated.
    setData(null);
    try {
      setData(await fetchRecommendation({
        lat: location.lat,
        lon: location.lng,
        farmAreaM2: location.areaM2,
        tankWaterL: Number(tankWater),
        plantingDate
      }));
    } catch (err) {
      setData(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecordPlanting(cropId = lastCropId, date = plantingDate) {
    if (savingRef.current || savedPlantings.includes(`${cropId}:${date}`)) return;
    if (!cropId || !date) {
      setSaveMessage({ error: true, text: "Select a crop and planting date before recording it." });
      return;
    }
    savingRef.current = true;
    setSaving(true);
    setSavingCropId(cropId);
    setSaveMessage(null);
    try {
      const records = await recordPlanting(cropId, date);
      setSavedPlantings((previous) => [...previous, `${cropId}:${date}`]);
      setHistory((previous) => [...records, ...previous]);
      setSaveMessage({ error: false, text: "Planting saved to history." });
      try {
        setHistory(await fetchHistory());
      } catch {
        setSaveMessage({ error: false, text: "Planting saved. Could not refresh older history; reload to try again." });
      }
    } catch (err) {
      setSaveMessage({ error: true, text: err.message });
    } finally {
      savingRef.current = false;
      setSaving(false);
      setSavingCropId(null);
    }
  }

  return (
    <>
      <Header />

      <main className="main-layout">

        <section className="map-section">
          <Map onLocationChange={handleLocationChange} />
        </section>

        <section className="farm-form">
          <h2>Farm Information</h2>
          <p>Enter your farm details to get started.</p>

          <div className="form-group">
            <label htmlFor="last-crop">Last Crop Planted</label>
            <select
              id="last-crop"
              value={lastCropId}
              onChange={(event) => setLastCropId(event.target.value)}
            >
              <option value="" disabled>Select crop</option>
              {crops.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="water-source">Water Source</label>
            <select id="water-source" value="Tank" readOnly disabled>
              <option value="Tank">Tank</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="planting-date">Planting Date</label>
            <input
              id="planting-date"
              type="date"
              value={plantingDate}
              onChange={(event) => setPlantingDate(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="tank-water">Amount of water in the tank (L)</label>
            <input
              id="tank-water"
              type="number"
              min="0"
              step="any"
              placeholder="e.g. 5000"
              value={tankWater}
              onChange={(event) => setTankWater(event.target.value)}
            />
          </div>

          <p className="form-readout">
            Farm area:{" "}
            {location ? `${Number(location.areaM2).toFixed(2)} m²` : "draw a boundary on the map"}
          </p>

          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={loading || !location}
          >
            {loading ? "Loading..." : "Analyze My Farm"}
          </button>

          <button
            className="secondary-btn"
            onClick={() => handleRecordPlanting()}
            disabled={saving || !lastCropId || savedPlantings.includes(`${lastCropId}:${plantingDate}`)}
          >
            {saving ? "Saving..." : "Record this planting"}
          </button>

          {!location && (
            <p className="analyze-hint">Draw your farm boundary on the map to enable analysis.</p>
          )}
        </section>
      </main>

      <Results
        data={data} loading={loading} error={error} history={history}
        onPlant={handleRecordPlanting} saving={saving} savingCropId={savingCropId}
        savedPlantings={savedPlantings} saveMessage={saveMessage}
      />
      <Footer />
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
