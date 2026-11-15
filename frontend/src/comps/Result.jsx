import "./Result.css";

const UNITS = {
  rainfall_mm: "mm",
  average: "°C",
  maximum: "°C",
  minimum: "°C",
  nitrogen_g_kg: "g/kg",
  surface_percent: "%",
  rootzone_percent: "%",
  distance_km: "km"
};

function DataTable({ title, dataset }) {
  if (!dataset) {
    return null;
  }

  const rows = dataset.rows || [];

  if (rows.length === 0) {
    return (
      <section className="result-card">
        <h2>{title}</h2>
        <p className="dataset-note">{dataset.error || "No data available."}</p>
      </section>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <section className="result-card">
      <h2>{title}</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>
                  {column.replace(/_/g, " ")}
                  {UNITS[column] ? ` (${UNITS[column]})` : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column}>{row[column]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function Results({ data, loading, error }) {
  return (
    <main className="results-page">
      <div className="results-header">
        <h1>Farm Analysis Results</h1>
        {data ? (
          <p>
            Live data for {Number(data.lat).toFixed(5)}, {Number(data.lon).toFixed(5)}
          </p>
        ) : (
          <p>Data loaded from the Terawise backend</p>
        )}
      </div>

      {loading && <p className="status-message">Loading data for your farm...</p>}
      {error && <p className="status-message error">{error}</p>}
      {!loading && !error && !data && (
        <p className="status-message">Click "Analyze My Farm" to load the results.</p>
      )}

      {data && (
        <>
          <DataTable title="Monthly Rainfall" dataset={data.rain} />
          <DataTable title="Monthly Temperature" dataset={data.temperature} />
          <DataTable title="Soil pH" dataset={data.ph} />
          <DataTable title="Soil Nitrogen" dataset={data.nitrogen} />
          <DataTable title="Soil Moisture" dataset={data.moisture} />
        </>
      )}
    </main>
  );
}
