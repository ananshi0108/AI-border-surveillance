import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000/api/v1";

function LiveCameras() {
  const [filter, setFilter] = useState("All");
const [search, setSearch] = useState("");
const [cameras, setCameras] = useState([]);
const [feedErrors, setFeedErrors] = useState({});

useEffect(() => {
  const fetchCameras = async () => {
    try {
      const response = await fetch(`${API_BASE}/cameras/`);

      if (!response.ok) {
        throw new Error("Failed to fetch cameras");
      }

      const data = await response.json();
      setCameras(data);
    } catch (error) {
      console.error("Error fetching cameras:", error);
    }
  };

  fetchCameras();
}, []);

  

 const filteredCameras = cameras.filter((camera) => {
  const matchesFilter =
    filter === "All" ||
    (filter === "Normal" && camera.status === "ONLINE") ||
    (filter === "Alerts" && camera.status === "OFFLINE") ||
    (filter === "Night Mode" && camera.mode === "Night Mode");

  const matchesSearch =
    String(camera.id).toLowerCase().includes(search.toLowerCase()) ||
    camera.location.toLowerCase().includes(search.toLowerCase());

  return matchesFilter && matchesSearch;
});

  return (
    <div className="camera-page">
      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Live Cameras</p>
          <h1>Live Camera Monitoring</h1>
          <p>Real-time surveillance feeds from border cameras</p>
        </div>

        <div className="camera-summary">
          <span className="online-dot"></span>
           {cameras.filter((camera) => camera.status === "ONLINE").length} /{" "}
           {cameras.length} Cameras Online
        </div>
      </div>

      <div className="camera-search">
  <input
  type="text"
  placeholder="Search camera by ID or location..."
  value={search}
  onChange={(e) => setSearch(e.target.value)}
/>
</div>
<div className="camera-toolbar">
        <button
          className={`filter-button ${
            filter === "All" ? "active-filter" : ""
          }`}
          onClick={() => setFilter("All")}
        >
          All Cameras
        </button>

        <button
          className={`filter-button ${
            filter === "Normal" ? "active-filter" : ""
          }`}
          onClick={() => setFilter("Normal")}
        >
          Normal
        </button>

        <button
          className={`filter-button ${
            filter === "Alerts" ? "active-filter" : ""
          }`}
          onClick={() => setFilter("Alerts")}
        >
          Alerts
        </button>

        <button
          className={`filter-button ${
            filter === "Night Mode" ? "active-filter" : ""
          }`}
          onClick={() => setFilter("Night Mode")}
        >
          Night Mode
        </button>
      </div>

      <div className="large-camera-grid">
        {filteredCameras.map((camera) => (
          <div className="large-camera-card" key={camera.id}>
            <div className="large-feed">
              <div className="feed-top">
                <span className="live-label">
                 ● {camera.status === "ONLINE" ? "LIVE" : "OFFLINE"}
                </span>

                <span className="camera-mode">
                  {camera.status}
                </span>
              </div>

              <div className="feed-center">
                {camera.status === "ONLINE" && !feedErrors[camera.id] ? (
                  <img
                    className="live-feed-img"
                    src={`${API_BASE}/cameras/${camera.id}/stream`}
                    alt={`Live AI-annotated feed for camera ${camera.id}`}
                    onError={() =>
                      setFeedErrors((prev) => ({ ...prev, [camera.id]: true }))
                    }
                  />
                ) : (
                  "📹"
                )}
              </div>

              {camera.status === "Alert" && (
                <div className="feed-alert">
                  ⚠ Security Event Detected
                </div>
              )}

              <div className="feed-camera-id">
                CAM-{String(camera.id).padStart(2, "0")}
              </div>
            </div>

            <div className="large-camera-info">
              <div className="camera-title">
                <div>
                  <h3>CAM-{String(camera.id).padStart(2, "0")}</h3>
                  <p>📍 {camera.location}</p>
                </div>

                <span
                 className={
                  camera.status === "ONLINE"
                  ? "status-normal"
                  : "status-alert"
                 }
                >
                   {camera.status}
                </span>
              </div>

              <div className="detection-info">
                <div>
                  <span>👤 Persons</span>
                  <strong>{camera.persons}</strong>
                </div>

                <div>
                  <span>🚗 Vehicles</span>
                  <strong>{camera.vehicles}</strong>
                </div>

                <div>
                  <span>AI Status</span>
                  <strong className="ai-active">
                    {camera.status === "ONLINE" ? "Active" : "Offline"}
                  </strong>
                </div>
              </div>

             <button className="camera-action">
  Open Full Screen
</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default LiveCameras;