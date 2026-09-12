import { useEffect, useState } from "react";

function Alerts() {
  const [filter, setFilter] = useState("All");
  const [alerts, setAlerts] = useState([]);
  const [reviewedAlerts, setReviewedAlerts] = useState([]);

  const liveCount = alerts.filter((alert) => alert.status === "NEW").length;

  useEffect(() => {
  const fetchAlerts = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/alerts/"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch alerts");
      }

      const data = await response.json();
      setAlerts(data);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  fetchAlerts();
}, []);



  const filteredAlerts =
    filter === "All"
      ? alerts
      : alerts.filter((alert) => alert.priority === filter);

  const markAsReviewed = async (id) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/v1/alerts/${id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status: "ACKNOWLEDGED",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update alert");
      }

      setReviewedAlerts((previous) => [...previous, id]);
      setAlerts((previous) =>
        previous.map((alert) =>
          alert.id === id
            ? { ...alert, status: "ACKNOWLEDGED" }
            : alert
        )
      );
    } catch (error) {
      console.error("Error updating alert:", error);
    }
  };

  return (
    <div className="alerts-page">
      <h1>Security Alerts</h1>

      <p>Monitor and review detected security events.</p>

      <div className="live-alert-count">
        🔴 {liveCount} Active Alerts
      </div>

      <div className="alert-filters">
        <button
          className={
            filter === "All"
              ? "filter-button active-filter"
              : "filter-button"
          }
          onClick={() => setFilter("All")}
        >
          All Alerts
        </button>

        <button
          className={
            filter === "High"
              ? "filter-button active-filter"
              : "filter-button"
          }
          onClick={() => setFilter("High")}
        >
          High Priority
        </button>

        <button
          className={
            filter === "Medium"
              ? "filter-button active-filter"
              : "filter-button"
          }
          onClick={() => setFilter("Medium")}
        >
          Medium
        </button>

        <button
          className={
            filter === "Low"
              ? "filter-button active-filter"
              : "filter-button"
          }
          onClick={() => setFilter("Low")}
        >
          Low
        </button>
      </div>

      <div className="alerts-list">
        {filteredAlerts.map((alert) => (
          <div className="alert-card" key={alert.id}>
            <h3>{alert.alert_type}</h3>

            <p>Camera: Camera {alert.camera_id}</p>

            <p>Zone: Zone {alert.zone_id}</p>

            <p>Target: {alert.target_class}</p>

            <p>Confidence: {(alert.confidence * 100).toFixed(1)}%</p>

            <p>Time: {new Date(alert.timestamp).toLocaleString()}</p>

            <small>Event ID: {alert.id}</small>

            <button
              className="review-alert-button"
              onClick={() => markAsReviewed(alert.id)}
            >
              {reviewedAlerts.includes(alert.id)
                ? "✓ Reviewed"
                : "✓ Mark as Reviewed"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Alerts;