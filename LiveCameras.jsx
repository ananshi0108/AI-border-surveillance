import { useState } from "react";

function LiveCameras() {
  const [filter, setFilter] = useState("All");
const [search, setSearch] = useState("");

  const cameras = [
    {
      id: "CAM-01",
      location: "North Gate",
      status: "Normal",
      persons: 4,
      vehicles: 2,
      mode: "Day Mode",
    },
    {
      id: "CAM-02",
      location: "East Sector",
      status: "Normal",
      persons: 2,
      vehicles: 1,
      mode: "Day Mode",
    },
    {
      id: "CAM-03",
      location: "West Sector",
      status: "Alert",
      persons: 7,
      vehicles: 3,
      mode: "Night Mode",
    },
    {
      id: "CAM-04",
      location: "South Gate",
      status: "Normal",
      persons: 3,
      vehicles: 1,
      mode: "Day Mode",
    },
    {
      id: "CAM-07",
      location: "Border Fence",
      status: "Alert",
      persons: 5,
      vehicles: 0,
      mode: "Night Mode",
    },
    {
      id: "CAM-12",
      location: "Main Road",
      status: "Normal",
      persons: 1,
      vehicles: 4,
      mode: "Day Mode",
    },
  ];

 const filteredCameras = cameras.filter((camera) => {
  const matchesFilter =
    filter === "All" ||
    (filter === "Normal" && camera.status === "Normal") ||
    (filter === "Alerts" && camera.status === "Alert") ||
    (filter === "Night Mode" && camera.mode === "Night Mode");

  const matchesSearch =
    camera.id.toLowerCase().includes(search.toLowerCase()) ||
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
           6 / 6 Cameras Online
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
                <span className="live-label">● LIVE</span>

                <span className="camera-mode">
                  {camera.mode}
                </span>
              </div>

              <div className="feed-center">
                📹
              </div>

              {camera.status === "Alert" && (
                <div className="feed-alert">
                  ⚠ Security Event Detected
                </div>
              )}

              <div className="feed-camera-id">
                {camera.id}
              </div>
            </div>

            <div className="large-camera-info">
              <div className="camera-title">
                <div>
                  <h3>{camera.id}</h3>
                  <p>{camera.location}</p>
                </div>

                <span
                  className={
                    camera.status === "Alert"
                      ? "status-alert"
                      : "status-normal"
                  }
                >
                  {camera.status}
                </span>
              </div>

              <div className="detection-info">
                <div>
                  <span>Persons</span>
                  <strong>{camera.persons}</strong>
                </div>

                <div>
                  <span>Vehicles</span>
                  <strong>{camera.vehicles}</strong>
                </div>

                <div>
                  <span>AI Status</span>
                  <strong className="ai-active">
                    Active
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