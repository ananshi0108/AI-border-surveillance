function Settings() {
  return (
    <div className="settings-page">

      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Settings</p>
          <h1>System Settings</h1>
          <p>Configure surveillance platform preferences</p>
        </div>
      </div>

      <div className="settings-grid">

        <div className="settings-card">
          <h3>System Configuration</h3>

          <div className="setting-row">
            <div>
              <strong>AI Detection</strong>
              <p>Enable AI-based object detection</p>
            </div>
            <span className="setting-on">Enabled</span>
          </div>

          <div className="setting-row">
            <div>
              <strong>Real-Time Alerts</strong>
              <p>Receive security event notifications</p>
            </div>
            <span className="setting-on">Enabled</span>
          </div>

          <div className="setting-row">
            <div>
              <strong>Night Vision</strong>
              <p>Enable low-light camera monitoring</p>
            </div>
            <span className="setting-on">Enabled</span>
          </div>
        </div>

        <div className="settings-card">
          <h3>Dashboard Preferences</h3>

          <div className="setting-row">
            <div>
              <strong>Refresh Interval</strong>
              <p>Dashboard data refresh frequency</p>
            </div>
            <select>
              <option>5 seconds</option>
              <option>10 seconds</option>
              <option>30 seconds</option>
            </select>
          </div>

          <div className="setting-row">
            <div>
              <strong>Alert Sound</strong>
              <p>Play sound when a high priority alert occurs</p>
            </div>
            <span className="setting-on">Enabled</span>
          </div>
        </div>

      </div>
    </div>
  );
}

export default Settings;