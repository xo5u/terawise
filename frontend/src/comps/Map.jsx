
import { useRef, useState } from "react";
import { MapContainer, TileLayer, FeatureGroup } from "react-leaflet";
import { EditControl } from "react-leaflet-draw";
import { area } from "@turf/area";

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

  // Calculate selected area
  function calculateArea(layer) {
    const squareMeters = area(layer.toGeoJSON());

    const acres = squareMeters / 4046.856;
    const hectares = squareMeters / 10000;

    setFarmArea({
      acres: acres.toFixed(2),
      hectares: hectares.toFixed(2),
      squareMeters: squareMeters.toFixed(2)
    });

    // Get the center of the selected farm
    const center = layer.getBounds().getCenter();

    setCoordinates({
      latitude: center.lat.toFixed(6),
      longitude: center.lng.toFixed(6)
    });
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
  }

  return (
    <div className="map-wrapper">

      <h2>Select Your Farm Area</h2>
      <p>Draw a rectangle or polygon around your farm.</p>

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

          <p>
            Latitude: {coordinates.latitude}
            <br />
            Longitude: {coordinates.longitude}
          </p>
        </div>
      )}

    </div>
  );
}
