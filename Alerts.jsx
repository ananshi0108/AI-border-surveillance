import { useEffect, useState } from "react";

function Alerts() {
  const [filter, setFilter] = useState("All");
  const [liveCount, setLiveCount] = useState(3);
  const [reviewedAlerts, setReviewedAlerts] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setLiveCount((count) => (count >= 5 ? 3 : count + 1));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const alerts = [
    {
      id: "ALT-001",
      type: "Unauthorized Entry",
      camera: "CAM-03",
      location: "West Sector",
      priority: "High",
      time: "2 minutes ago",
    },
    {
      id: "ALT-002",
      type: "Suspicious Vehicle",
      camera: "CAM-01",
      location: "North Gate",
      priority: "Medium",
      time: "8 minutes ago",
    },
    {
      id: "ALT-003",
      type: "Person Detected",
      camera: "CAM-04",
      location: "South Gate",
      priority: "Low",
      time: "15 minutes ago",
    },
  ];

  const filteredAlerts =
    filter === "All"
      ? alerts
      : alerts.filter((alert) => alert.priority === filter);

  const markAsReviewed = (id) => {
    setReviewedAlerts((previous) => [...previous, id]);
  };

  return (
    <div className="alerts-page">
      <h1>Security Alerts</h1>

      <p>Monitor and review detected security events.</p>

      <div className="live-alert-count">
        {liveCount} Active Alerts
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
            <h3>{alert.type}</h3>

            <p>Camera: {alert.camera}</p>

            <p>Location: {alert.location}</p>

            <p>Priority: {alert.priority}</p>

            <p>Time: {alert.time}</p>

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