
import { useRef, useState } from "react";
import { MapContainer, TileLayer, FeatureGroup } from "react-leaflet";
import { EditControl } from "react-leaflet-draw";
import { area } from "@turf/area";
import { centroid } from "@turf/centroid";

import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import "./Map.css";

export default function Map() {
  const position = [39.8283, -98.5795];

  const usaBounds = [
    [24.0, -125.0],
    [49.5, -66.0]
  ];

  const featureGroupRef = useRef(null);

  const [farmArea, setFarmArea] = useState(null);
  const [coordinates, setCoordinates] = useState(null);
  const [farmAddress, setFarmAddress] = useState("");
  const [loadingAddress, setLoadingAddress] = useState(false);
  const [apiStatus, setApiStatus] = useState("");

  // Get readable address from coordinates
  async function getAddress(lat, lng) {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`
    );

    if (!response.ok) {
      throw new Error("Could not retrieve farm address");
    }

    const data = await response.json();

    return data.display_name || "Address not found";
  }

  // Send coordinates to FastAPI
  async function sendLocation(lat, lng) {
    const response = await fetch("http://127.0.0.1:8000/api/location", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        lat: lat,
        lng: lng
      })
    });

    if (!response.ok) {
      throw new Error("Failed to send location to backend");
    }

    return await response.json();
  }

  // Calculate farm area and retrieve its location
  async function calculateArea(layer) {
    const geoJSON = layer.toGeoJSON();

    // Calculate area
    const squareMeters = area(geoJSON);

    const acres = squareMeters / 4046.8564224;
    const hectares = squareMeters / 10000;

    setFarmArea({
      acres: acres.toFixed(2),
      hectares: hectares.toFixed(2),
      squareMeters: squareMeters.toFixed(2)
    });

    // Calculate polygon centroid
    const center = centroid(geoJSON);
    const [longitude, latitude] = center.geometry.coordinates;

    setCoordinates({
      latitude: latitude.toFixed(6),
      longitude: longitude.toFixed(6)
    });

    // Get address and send location
    setLoadingAddress(true);
    setFarmAddress("");
    setApiStatus("");

    try {
      const address = await getAddress(latitude, longitude);
      setFarmAddress(address);

      const result = await sendLocation(latitude, longitude);

      console.log("Backend response:", result);
      setApiStatus("Location sent successfully");
    } catch (error) {
      console.error("Error:", error);
      setApiStatus(error.message);
    } finally {
      setLoadingAddress(false);
    }
  }

  // When user finishes drawing
  function handleCreated(e) {
    const layer = e.layer;
    const group = featureGroupRef.current;

    // Keep only one farm boundary
    group.eachLayer((existingLayer) => {
      if (existingLayer !== layer) {
        group.removeLayer(existingLayer);
      }
    });

    calculateArea(layer);
  }

  // When user edits the boundary
  function handleEdited(e) {
    e.layers.eachLayer((layer) => {
      calculateArea(layer);
    });
  }

  // When user deletes the boundary
  function handleDeleted() {
    setFarmArea(null);
    setCoordinates(null);
    setFarmAddress("");
    setApiStatus("");
  }

  return (
    <div className="map-wrapper">
      <h2>Select Your Farm Area</h2>
      <p>Draw a polygon around your farm boundary.</p>
      <p>
            <strong>Address:</strong>{" "}
            {loadingAddress
              ? "Getting address..."
              : farmAddress || "Address unavailable"}
      </p>

      <MapContainer
        center={position}
        zoom={4}
        minZoom={4}
        maxZoom={19}
        maxBounds={usaBounds}
        maxBoundsViscosity={1.0}
        className="farm-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FeatureGroup ref={featureGroupRef}>
          <EditControl
            position="topright"
            onCreated={handleCreated}
            onEdited={handleEdited}
            onDeleted={handleDeleted}
            draw={{
              rectangle: false,
              polygon: true,
              polyline: false,
              circle: false,
              marker: false,
              circlemarker: false
            }}
          />
        </FeatureGroup>
      </MapContainer>

      {farmArea && (
        <div className="area-result">
          <h3>Selected Farm Area</h3>

          <div className="area-values">
            <div>
              <span>Acres</span>
              <strong>{farmArea.acres}</strong>
            </div>

            <div>
              <span>Hectares</span>
              <strong>{farmArea.hectares}</strong>
            </div>
          </div>

          <p>Area: {farmArea.squareMeters} m²</p>

          <h4>Farm Location</h4>

          {coordinates && (
            <>
              <p>Latitude: {coordinates.latitude}</p>
              <p>Longitude: {coordinates.longitude}</p>
            </>
          )}

          <p>{apiStatus}</p>
        </div>
      )}
    </div>
  );
}
