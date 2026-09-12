import { useState } from "react";

function Settings() {
  const [nightMode, setNightMode] = useState(true);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  return (
    <div className="settings-page">
      <h1>System Settings</h1>
      <p>Configure surveillance system preferences and controls.</p>

      <div className="settings-card">
        <h2>General Settings</h2>

        <div className="setting-row">
          <div>
            <strong>Night Surveillance Mode</strong>
            <small>Optimize the interface for night monitoring.</small>
          </div>

          <button
            className={nightMode ? "toggle-button on" : "toggle-button"}
            onClick={() => setNightMode(!nightMode)}
          >
            {nightMode ? "ON" : "OFF"}
          </button>
        </div>

        <div className="setting-row">
          <div>
            <strong>Security Alerts</strong>
            <small>Receive notifications for detected security events.</small>
          </div>

          <button
            className={alertsEnabled ? "toggle-button on" : "toggle-button"}
            onClick={() => setAlertsEnabled(!alertsEnabled)}
          >
            {alertsEnabled ? "ON" : "OFF"}
          </button>
        </div>

        <div className="setting-row">
          <div>
            <strong>Automatic Refresh</strong>
            <small>Automatically update surveillance information.</small>
          </div>

          <button
            className={autoRefresh ? "toggle-button on" : "toggle-button"}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      <div className="settings-card">
        <h2>System Information</h2>

        <div className="system-info">
          <div>
            <span>Platform</span>
            <strong>IBVAP</strong>
          </div>

          <div>
            <span>System Status</span>
            <strong className="operational">Operational</strong>
          </div>

          <div>
            <span>Environment</span>
            <strong>SIH 2026 Prototype</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;