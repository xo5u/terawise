
import "./Result.css";

const crops = [
  {
    name: "Wheat",
    suitability: 95,
    water: "450 mm / season",
    profit: "$850"
  },
  {
    name: "Soybeans",
    suitability: 89,
    water: "500 mm / season",
    profit: "$720"
  },
  {
    name: "Corn",
    suitability: 84,
    water: "550 mm / season",
    profit: "$680"
  }
];

export default function Results() {
  return (
    <main className="results-page">

      <div className="results-header">
        <h1>Farm Analysis Results</h1>
        <p>Your personalized agricultural recommendations</p>
      </div>

      {/* Water Requirements */}
      <section className="result-card water-card">
        <h2>Water Requirements</h2>

        <div className="water-content">
          <div>
            <span>Estimated Water Needed</span>
            <h3>4,200 L</h3>
            <p>Per week</p>
          </div>

          <div className="water-details">
            <div>
              <span>Daily</span>
              <strong>600 L</strong>
            </div>
            <div>
              <span>Seasonal</span>
              <strong>75,000 L</strong>
            </div>
          </div>
        </div>
      </section>

      {/* Top 3 Crops */}
      <section className="result-card">
        <h2>Top 3 Recommended Crops</h2>
        <p>Best crops based on your farm conditions</p>

        <div className="crop-list">
          {crops.map((crop, index) => (
            <div className="crop-row" key={crop.name}>
              <div className="crop-rank">
                #{index + 1}
              </div>

              <div className="crop-info">
                <h3>{crop.name}</h3>
                <span>Suitability: {crop.suitability}%</span>
                <div className="crop-progress">
                  <div style={{ width: `${crop.suitability}%` }} />
                </div>
              </div>

              <div className="crop-info-right">
                <span>Water requirement</span>
                <strong>{crop.water}</strong>
                <span>Estimated profit / acre</span>
                <strong className="profit">{crop.profit}</strong>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Profit Estimation */}
      <section className="result-card profit-card">
        <h2>Profit Estimation</h2>
        <p>Estimated financial return for your recommended crop</p>

        <div className="profit-content">
          <div>
            <span>Expected Revenue</span>
            <strong>$1,500</strong>
          </div>

          <div>
            <span>Production Costs</span>
            <strong>$650</strong>
          </div>

          <div className="net-profit">
            <span>Estimated Net Profit</span>
            <strong>$850 / acre</strong>
          </div>
        </div>
      </section>

    </main>
  );
}
