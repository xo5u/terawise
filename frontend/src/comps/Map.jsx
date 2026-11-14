
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./Map.css";

export default function Map() {
  const position = [39.8283, -98.5795];

  // Approximate boundaries of the contiguous USA
  const usaBounds = [
    [24.0, -125.0], // Southwest
    [49.5, -66.0]   // Northeast
  ];

  return (
    <div className="map-wrapper">
      <h2>Select Your Farm Location</h2>
      <p>Choose a location within the United States.</p>

      <MapContainer
        center={position}
        zoom={4}
        minZoom={4}
        maxBounds={usaBounds}
        maxBoundsViscosity={1.0}
        className="farm-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <Marker position={position}>
          <Popup>
            United States
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
