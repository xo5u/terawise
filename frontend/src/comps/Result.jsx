import { useEffect, useState } from "react";
import "./Result.css";

const DEMAND_LABEL = { L: "Low demand", M: "Medium demand", H: "High demand" };
const HISTORY_PAGE_SIZE = 5;

function litres(value) {
  if (value === null || value === undefined) return "-";
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })} L`;
}

function Environment({ environment }) {
  const errors = environment.source_errors || {};
  const rows = [
    ["Soil type", environment.soil_texture_class],
    ["Soil moisture", environment.soil_moisture_percent === null ? null : `${environment.soil_moisture_percent} %`],
    ["Soil nitrogen", environment.nitrogen_g_kg === null ? null : `${environment.nitrogen_g_kg} g/kg`],
    ["Soil pH", environment.ph === null || environment.ph === undefined
      ? null
      : `${environment.ph} (${environment.ph_source})`]
  ];

  return (
    <section className="result-card">
      <h2>Measured Conditions</h2>
      <div className="env-grid">
        {rows.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value === null || value === undefined ? "unavailable" : value}</strong>
          </div>
        ))}
      </div>
      {Object.keys(errors).length > 0 && (
        <p className="dataset-note">
          Unavailable sources: {Object.entries(errors).map(([k, v]) => `${k} (${v})`).join("; ")}
        </p>
      )}
    </section>
  );
}

function Fertilizer({ fertilizer }) {
  if (!fertilizer) return null;

  if (fertilizer.status === "sufficient") {
    return <p className="rec-line">Fertilizer: none needed — measured nitrogen already meets the requirement.</p>;
  }

  if (fertilizer.status === "cannot_calculate") {
    return (
      <div className="rec-line">
        <p>
          Nitrogen shortfall: {fertilizer.nitrogen_deficit_g_per_kg} g/kg. Fertilizer quantity cannot be
          calculated — {fertilizer.reason}
        </p>
        {fertilizer.available_products && fertilizer.available_products.length > 0 && (
          <p className="dataset-note">
            Available products:{" "}
            {fertilizer.available_products
              .map((p) => `${p.product_name} (${p.nitrogen_percent}% N)`)
              .join(", ")}
          </p>
        )}
      </div>
    );
  }

  return <p className="rec-line">Fertilizer: {fertilizer.reason}</p>;
}

function Recommendation({ crop, index, onPlant, saving, savingCropId, saved }) {
  return (
    <article className="rec-card">
      <header className="rec-header">
        <h3>
          {index + 1}. {crop.name}
        </h3>
        <span className="rec-score">{crop.suitability_percent}%</span>
      </header>

      <p className="rec-sub">
        {DEMAND_LABEL[crop.demand] || crop.demand} · {crop.growth_duration_months} months ·
        harvest {crop.expected_harvest}
      </p>

      <div className="rec-grid">
        <div><span>Plants</span><strong>{crop.plant_count}</strong></div>
        <div><span>Water needed</span><strong>{litres(crop.required_water_l)}</strong></div>
        <div><span>Tank water</span><strong>{litres(crop.tank_water_l)}</strong></div>
        <div><span>Effective rainfall</span><strong>{litres(crop.effective_rainfall_l)}</strong></div>
        <div><span>Water surplus</span><strong>{litres(crop.water_surplus_l)}</strong></div>
        <div><span>Growth multiplier</span><strong>{crop.growth_multiplier}×</strong></div>
      </div>

      <Fertilizer fertilizer={crop.fertilizer} />

      {crop.timeline && crop.timeline.length > 0 && (
        <details className="rec-timeline">
          <summary>Planting to harvest ({crop.timeline.length} months)</summary>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Estimated water demand (L)</th>
                  <th>Rainfall (mm)</th>
                  <th>Mean temp (°C)</th>
                </tr>
              </thead>
              <tbody>
                {crop.timeline.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{row.estimated_water_demand_l}</td>
                    <td>{row.rainfall_mm}</td>
                    <td>{row.mean_temperature_c}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="dataset-note">
            Monthly water values are estimates: the total is distributed evenly across the growth
            duration. Rainfall is a historical monthly average, not a forecast.
          </p>
        </details>
      )}

      <p className="dataset-note">
        Calculated as an alternative use of the whole farm area, not combined with the other
        recommendations.
      </p>
      <button
        type="button"
        className="plant-btn"
        onClick={onPlant}
        disabled={saving || saved}
      >
        {savingCropId === crop.crop_id ? "Saving..." : saved ? "Saved to history" : `Plant ${crop.name}`}
      </button>
    </article>
  );
}

function HistoryPanel({ history }) {
  const [page, setPage] = useState(0);
  useEffect(() => { setPage(0); }, [history]);

  if (!history || history.length === 0) {
    return (
      <section className="result-card">
        <h2>Planting History</h2>
        <p className="dataset-note">No plantings recorded yet.</p>
      </section>
    );
  }

  const pages = Math.ceil(history.length / HISTORY_PAGE_SIZE);
  const rows = history.slice(page * HISTORY_PAGE_SIZE, (page + 1) * HISTORY_PAGE_SIZE);

  return (
    <section className="result-card">
      <h2>Planting History</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Plant</th>
              <th>Demand</th>
              <th>Planted</th>
              <th>Harvested</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.plant_name || "-"}</td>
                <td>{row.soil_nutrition_demand || "-"}</td>
                <td>{row.planting_date || "-"}</td>
                <td>{row.harvest_date || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="pager">
          <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
            Previous
          </button>
          <span>
            Page {page + 1} of {pages}
          </span>
          <button onClick={() => setPage((p) => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1}>
            Next
          </button>
        </div>
      )}
    </section>
  );
}

export default function Results({ data, loading, error, history, onPlant, saving, savingCropId, savedPlantings = [], saveMessage }) {
  return (
    <main className="results-page">
      <div className="results-header">
        <h1>Crop Recommendations</h1>
        {data ? (
          <p>
            {Number(data.location.lat).toFixed(5)}, {Number(data.location.lon).toFixed(5)} ·{" "}
            {Number(data.inputs.farm_area_m2).toFixed(2)} m² · tank {litres(data.inputs.tank_water_l)} ·
            planting {data.inputs.planting_date}
          </p>
        ) : (
          <p>Draw your farm, enter your tank water, then analyze.</p>
        )}
      </div>

      {loading && <p className="status-message">Checking crops against your farm conditions...</p>}
      {error && <p className="status-message error">{error}</p>}
      {saveMessage && (
        <p className={`status-message${saveMessage.error ? " error" : " success"}`} role={saveMessage.error ? "alert" : "status"}>
          {saveMessage.text}
        </p>
      )}

      {data && (
        <>
          <Environment environment={data.environment} />

          {data.recommendations.length === 0 ? (
            <section className="result-card">
              <h2>No suitable crops</h2>
              <p className="dataset-note">
                No low or medium nutrient-demand crop passed the soil, area and water checks for this
                farm. High demand crops are never recommended.
              </p>
              {data.water_shortfalls && data.water_shortfalls.length > 0 && (
                <>
                  <p className="rec-line">
                    Closest on water — these qualify if more water is available:
                  </p>
                  <ul className="reason-list">
                    {data.water_shortfalls.map((crop) => (
                      <li key={crop.name}>
                        <strong>{crop.name}</strong>: needs{" "}
                        {litres(crop.additional_water_needed_l)} more ({litres(crop.required_water_l)}{" "}
                        required, {litres(crop.available_water_l)} available)
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          ) : (
            <section className="result-card">
              <h2>
                Top {data.recommendations.length}{" "}
                {data.selected_category === "L" ? "low" : "medium"} nutrient-demand crops
              </h2>
              {data.selected_category === "M" && (
                <p className="dataset-note">
                  No low-demand crop qualified, so medium-demand crops are shown as a fallback.
                </p>
              )}
              {data.recommendations.map((crop, index) => (
                <Recommendation
                  key={crop.crop_id} crop={crop} index={index}
                  onPlant={() => onPlant(crop.crop_id, data.inputs.planting_date)}
                  saving={saving} savingCropId={savingCropId}
                  saved={savedPlantings.includes(`${crop.crop_id}:${data.inputs.planting_date}`)}
                />
              ))}
            </section>
          )}

          {data.insufficient_data.length > 0 && (
            <section className="result-card">
              <h2>Not assessed ({data.insufficient_data.length})</h2>
              <ul className="reason-list">
                {data.insufficient_data.map((crop) => (
                  <li key={crop.crop_id}>
                    <strong>{crop.name}</strong>: {crop.reason}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.excluded.length > 0 && (
            <details className="result-card">
              <summary>
                <h2>Excluded crops ({data.excluded.length})</h2>
              </summary>
              <ul className="reason-list">
                {data.excluded.map((crop) => (
                  <li key={crop.crop_id}>
                    <strong>{crop.name}</strong>: {crop.reason}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}

      <HistoryPanel history={history} />
    </main>
  );
}
