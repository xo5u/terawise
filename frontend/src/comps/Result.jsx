import "./Result.css";

function DataTable({ title, rows }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return (
      <section className="result-card">
        <h2>{title}</h2>
        <p>No data available.</p>
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
                <th key={column}>{column.replace(/_/g, " ")}</th>
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
        <p>Data loaded from the Terawise backend</p>
      </div>

      {loading && <p className="status-message">Loading data...</p>}
      {error && <p className="status-message error">{error}</p>}
      {!loading && !error && !data && (
        <p className="status-message">Click "Analyze My Farm" to load the results.</p>
      )}

      {data && (
        <>
          <DataTable title="Monthly Rainfall" rows={data.rain} />
          <DataTable title="Monthly Temperature" rows={data.temperature} />
          <DataTable title="Soil pH" rows={data.ph} />
        </>
      )}
    </main>
  );
}