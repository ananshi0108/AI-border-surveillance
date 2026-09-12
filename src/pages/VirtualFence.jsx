import { useEffect, useState } from "react";

function VirtualFence() {
  const [selectedCamera, setSelectedCamera] = useState(1);
  const [fenceSaved, setFenceSaved] = useState(true);
  const [drawing, setDrawing] = useState(false);
  const [fencePoints, setFencePoints] = useState([]);
  const [zones, setZones] = useState([]);

  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/v1/cameras/"
        );

        if (!response.ok) {
          throw new Error("Failed to fetch cameras");
        }

        const data = await response.json();
        setCameras(data);

        if (data.length > 0) {
          setSelectedCamera(data[0].id);
        }
      } catch (error) {
        console.error("Error fetching cameras:", error);
      }
    };

    fetchCameras();
  }, []);

  useEffect(() => {
    const fetchZones = async () => {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/v1/zones/"
        );

        if (!response.ok) {
          throw new Error("Failed to fetch zones");
        }

        const data = await response.json();
        setZones(data);

        const polygonZone = data.find(
          (zone) =>
            zone.camera_id === Number(selectedCamera) &&
            zone.zone_type === "POLYGON" &&
            zone.is_active
        );

        if (polygonZone) {
          setFencePoints(
            polygonZone.coordinates.map(([x, y]) => ({
              x: x * 100,
              y: y * 100,
            }))
          );
          setFenceSaved(true);
        }
      } catch (error) {
        console.error("Error fetching zones:", error);
      }
    };

    fetchZones();
  }, [selectedCamera]);

  const clearFence = () => {
    setFenceSaved(false);
    setDrawing(false);
    setFencePoints([]);
  };

  const saveFence = async () => {
  if (fencePoints.length < 3) {
    alert("Please select at least 3 points.");
    return;
  }

  try {
    const response = await fetch(
      "http://127.0.0.1:8000/api/v1/zones/",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          camera_id: Number(selectedCamera),
          name: "Restricted Area",
          zone_type: "POLYGON",
          coordinates: fencePoints.map((point) => [
            point.x / 100,
            point.y / 100,
          ]),
          trigger_type: "ALL",
          is_active: true,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Failed to save fence");
    }

    await response.json();

    setFenceSaved(true);
    setDrawing(false);

    alert("Fence saved successfully.");
  } catch (error) {
    console.error("Error saving fence:", error);
    alert("Failed to save fence.");
  }
};

  const handleCameraClick = (e) => {
    if (!drawing) return;

    const rect = e.currentTarget.getBoundingClientRect();

    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    setFencePoints((previous) => [
      ...previous,
      { x: x, y: y },
    ]);
  };

  return (
    <div className="virtual-fence-page">

      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Virtual Fence</p>

          <h1>Virtual Fence Configuration</h1>

          <p>
            Define restricted surveillance zones for AI-based intrusion detection
          </p>
        </div>

        <div className="fence-status">
          <span className="online-dot"></span>
          Fence Monitoring Active
        </div>
      </div>

      <div className="fence-controls">

        <div className="control-group">
          <label>Select Camera</label>

          <select
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value)}
          >
            {cameras.map((camera) => (
              <option key={camera.id} value={camera.id}>
                CAM-{String(camera.id).padStart(2, "0")} — {camera.location}
              </option>
            ))}
          </select>
        </div>

        <div className="fence-buttons">

          <button
            className="draw-fence-button"
            onClick={() => {
              setDrawing(true);
              setFencePoints([]);
              setFenceSaved(false);
            }}
          >
            ✏️ {drawing ? "Drawing..." : "Draw Fence"}
          </button>

          <button
            className="clear-fence-button"
            onClick={clearFence}
          >
            🗑 Clear
          </button>

          <button
            className="save-fence-button"
            onClick={saveFence}
          >
            ✓ Save Fence
          </button>

        </div>
      </div>

      <div className="fence-workspace">

        <div className="fence-camera">

          <div className="fence-camera-top">
            <span className="live-label">● LIVE</span>

            <span>
               CAM-{String(selectedCamera).padStart(2, "0")}
            </span>
          </div>

          <div
            className={
              "mock-camera-feed " +
              (drawing ? "fence-drawing-mode" : "")
            }
            onClick={handleCameraClick}
          >

            <div className="camera-grid-lines"></div>

            {fenceSaved && fencePoints.length === 0 && (
              <div className="virtual-fence-polygon">
                <div className="fence-point point-1"></div>
                <div className="fence-point point-2"></div>
                <div className="fence-point point-3"></div>
                <div className="fence-point point-4"></div>
              </div>
            )}

            {fencePoints.length >= 3 && (
  <svg
    className="drawn-fence-lines"
    viewBox="0 0 100 100"
    preserveAspectRatio="none"
  >
    <polygon
      points={fencePoints
  .map((point) => point.x + "," + point.y)
  .join(" ")}
    />
  </svg>
)}
{fencePoints.map((point, index) => (
              <div
                key={index}
                className="drawn-fence-point"
                style={{
                  left: point.x + "%",
                  top: point.y + "%",
                }}
              >
                {index + 1}
              </div>
            ))}

            <div className="camera-placeholder">
              📹
              <span>Camera Feed</span>
            </div>

            <div className="camera-overlay">
              <span>{selectedCamera}</span>
              <span>AI ANALYTICS ACTIVE</span>
            </div>

          </div>

          {drawing && fencePoints.length > 0 && (
  <div className="fence-point-count">
    📍 {fencePoints.length} points selected
  </div>
)}
<div className="fence-instruction">

            {drawing ? (
              <>
                ✏️ <strong>Drawing mode active.</strong>{" "}
                Click on the camera feed to create fence points.
              </>
            ) : (
              <>
                💡 Click <strong>Draw Fence</strong> to define a restricted
                surveillance area.
              </>
            )}

          </div>

        </div>

        <div className="fence-settings">

          <h3>Fence Settings</h3>

          <div className="setting-item">
            <span>Fence Status</span>

            <strong
              className={
                fenceSaved
                  ? "fence-active"
                  : "fence-inactive"
              }
            >
              {fenceSaved ? "Active" : "Not Configured"}
            </strong>
          </div>

          <div className="setting-item">
            <span>Camera</span>
            <strong>{selectedCamera}</strong>
          </div>

          <div className="setting-item">
            <span>Detection</span>
            <strong>Person / Vehicle</strong>
          </div>

          <div className="setting-item">
            <span>Alert Trigger</span>
            <strong>Instant</strong>
          </div>

          <div className="setting-item">
            <span>Zone Type</span>
            <strong>Restricted Area</strong>
          </div>

          <div className="fence-note">
            ⚠️ Any person or vehicle entering the configured zone will
            generate a security alert.
          </div>

        </div>

      </div>

    </div>
  );
}

export default VirtualFence;