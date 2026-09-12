import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function BorderMap() {
  const cameras = [
    {
      id: "CAM-01",
      location: "North Gate",
      position: [28.6139, 77.2090],
      status: "Normal",
    },
    {
      id: "CAM-03",
      location: "West Sector",
      position: [28.6200, 77.2000],
      status: "Alert",
    },
    {
      id: "CAM-04",
      location: "South Gate",
      position: [28.6050, 77.2150],
      status: "Normal",
    },
    {
      id: "CAM-07",
      location: "Border Fence",
      position: [28.6250, 77.2200],
      status: "Alert",
    },
  ];

  return (
    <div className="border-map-page">
      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Border Map</p>
          <h1>Border Surveillance Map</h1>
          <p>Monitor camera locations and security events</p>
        </div>
      </div>

      <div className="map-card">
        <MapContainer
          center={[28.6139, 77.2090]}
          zoom={13}
          style={{ height: "550px", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {cameras.map((camera) => (
            <Marker
              key={camera.id}
              position={camera.position}
            >
              <Popup>
                <strong>{camera.id}</strong>
                <br />
                {camera.location}
                <br />
                Status: {camera.status}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}

export default BorderMap;