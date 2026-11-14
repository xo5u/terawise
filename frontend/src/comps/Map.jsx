
import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./Map.css";

const defaultPosition = [39.8283, -98.5795];

function LocationMarker({ position, onSelect }) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng);
    },
  });

  return (
    <Marker position={position}>
      <Popup>
        {position[0].toFixed(4)}, {position[1].toFixed(4)}
      </Popup>
    </Marker>
  );
}

export default function Map() {
  const [position, setPosition] = useState(defaultPosition);
  const [error, setError] = useState(null);

  // Approximate boundaries of the contiguous USA
  const usaBounds = [
    [24.0, -125.0], // Southwest
    [49.5, -66.0]   // Northeast
  ];

  async function handleSelect(latlng) {
    setPosition([latlng.lat, latlng.lng]);
    setError(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: latlng.lat, lng: latlng.lng }),
      });

      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const confirmed = await res.json();
      setPosition([confirmed.lat, confirmed.lng]);
    } catch (err) {
      setError("Could not reach the server to confirm this location.");
    }
  }

  return (
    <div className="map-wrapper">
      <h2>Select Your Farm Location</h2>
      <p>Click anywhere within the United States to drop a pin.</p>
      <p className="map-coords">
        Lat: {position[0].toFixed(4)}, Lng: {position[1].toFixed(4)}
      </p>
      {error && <p className="map-error">{error}</p>}

      <MapContainer
        center={defaultPosition}
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

        <LocationMarker position={position} onSelect={handleSelect} />
      </MapContainer>
    </div>
  );
}
