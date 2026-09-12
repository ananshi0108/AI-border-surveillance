import {useEffect , useState } from "react";
import './index.css';
import LiveCameras from "./pages/LiveCameras";
import Alerts from "./pages/Alerts";
import BorderMap from "./pages/BorderMap";
import EventHistory from "./pages/EventHistory";
import Analytics from "./pages/Analytics";
import VirtualFence from "./pages/VirtualFence";
import Settings from "./pages/Settings";
import Login from "./pages/Login";

const pageInfo = {
  dashboard: {
    breadcrumb: "Dashboard / Overview",
    title: "Border Surveillance Dashboard",
    subtitle: "Intelligent Border Video Analytics Platform",
  },
  cameras: {
    breadcrumb: "Dashboard / Live Cameras",
    title: "Live Camera Monitoring",
    subtitle: "Real-time surveillance feeds from border cameras",
  },
  alerts: {
    breadcrumb: "Dashboard / Alerts",
    title: "Security Alerts",
    subtitle: "Monitor and review detected security events",
  },
  map: {
    breadcrumb: "Dashboard / Border Map",
    title: "Border Surveillance Map",
    subtitle: "Live camera locations and security status",
  },
  events: {
    breadcrumb: "Dashboard / Event History",
    title: "Event History",
    subtitle: "Review and track historical surveillance events",
  },
  analytics: {
    breadcrumb: "Dashboard / Analytics",
    title: "Surveillance Analytics",
    subtitle: "Detection activity and security event analysis",
  },
  fence: {
    breadcrumb: "Dashboard / Virtual Fence",
    title: "Virtual Fence Configuration",
    subtitle: "Define restricted surveillance zones",
  },
};
function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [liveDetections, setLiveDetections] = useState(27);
  useEffect(() => {
  const interval = setInterval(() => {
    setLiveDetections((count) => (count >= 35 ? 27 : count + 1));
  }, 4000);

  return () => clearInterval(interval);
}, []);
  if (!isLoggedIn) {
  return <Login onLogin={() => setIsLoggedIn(true)} />;
}
  return (
    <div className="app">

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">I</div>
          <div>
            <h2>IBVAP</h2>
            <span>Border Analytics</span>
          </div>
        </div>

        <nav>
  <a
    className={activePage === "dashboard" ? "active" : ""}
    onClick={() => setActivePage("dashboard")}
  >
    Dashboard
  </a>

  <a
    className={activePage === "cameras" ? "active" : ""}
    onClick={() => setActivePage("cameras")}
  >
    Live Cameras
  </a>

  <a
    className={activePage === "alerts" ? "active" : ""}
    onClick={() => setActivePage("alerts")}
  >
    Alerts
  </a>

  <a
    className={activePage === "map" ? "active" : ""}
    onClick={() => setActivePage("map")}
  >
    Border Map
  </a>

  <a
    className={activePage === "events" ? "active" : ""}
    onClick={() => setActivePage("events")}
  >
    Event History
  </a>

  <a
    className={activePage === "analytics" ? "active" : ""}
    onClick={() => setActivePage("analytics")}
  >
    Analytics
  </a>

  <a
    className={activePage === "fence" ? "active" : ""}
    onClick={() => setActivePage("fence")}
  >
    Virtual Fence
  </a>

  <a
  className={activePage === "settings" ? "active" : ""}
  onClick={() => setActivePage("settings")}
>
  Settings
</a>
</nav>
        <div className="system-status">
          <span className="status-dot"></span>
          <div>
            <strong>System Online</strong>
            <small>All services operational</small>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">

        <header className="topbar">
          <div>
            <p className="breadcrumb">
  {pageInfo[activePage].breadcrumb}
</p>

<h1>
  {pageInfo[activePage].title}
</h1>

<p className="subtitle">
  {pageInfo[activePage].subtitle}
</p>
          </div>

          <div className="user-section">
            <button
  className="notification-button"
  onClick={() => setActivePage("alerts")}
>
  
  <span className="notification-count">3</span>
</button>
            <div className="live-badge">
              <span></span> SYSTEM LIVE
            </div>
           <div className="admin">
  <div className="avatar">A</div>

  <div>
    <strong>Administrator</strong>
    <small>Control Room</small>
  </div>

  <button
    className="logout-button"
    onClick={() => setIsLoggedIn(false)}
  >
    Logout
  </button>
</div>
</div>
        </header>

       {activePage === "cameras" ? (
  <LiveCameras />
) : activePage === "alerts" ? (
  <Alerts />
) : activePage === "map" ? (
  <BorderMap />
) : activePage === "events" ? (
  <EventHistory />
) : activePage === "analytics" ? (
  <Analytics />
) : activePage === "fence" ? (
  <VirtualFence />
) : activePage === "settings" ? (
  <Settings />
) : (
 <>
    {/* dashboard */}
 
    {/* Statistics */}
    <section className="stats-grid">

          <div className="stat-card">
            <div className="stat-icon camera">📹</div>
            <div>
              <p>Active Cameras</p>
              <h2>24</h2>
              <span className="positive">● 22 online</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon alert">🚨</div>
            <div>
              <p>Active Alerts</p>
              <h2>03</h2>
              <span className="warning">3 high priority</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon person">👤</div>
            <div>
              <p>Persons Detected</p>
              <h2>{liveDetections}</h2>
              <span className="positive">↑ 12% today</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon vehicle">🚙</div>
            <div>
              <p>Vehicles Detected</p>
              <h2>86</h2>
              <span className="positive">↑ 8% today</span>
            </div>
          </div>

        </section>

        {/* Dashboard Grid */}
        <section className="dashboard-grid">

          {/* Camera Feed */}
          <div className="panel camera-panel">
            <div className="panel-header">
              <div>
                <h3>Live Camera Feeds</h3>
                <p>Real-time border monitoring</p>
              </div>
              <button onClick={() => setActivePage("cameras")}>
  View All
</button>
            </div>

            <div className="camera-grid">

              <div className="camera-feed">
                <div className="feed-screen">
                  <span className="recording">● LIVE</span>
                  <div className="camera-placeholder">📹</div>
                </div>
                <div className="feed-info">
                  <strong>Camera 01</strong>
                  <span>North Gate</span>
                </div>
              </div>

              <div className="camera-feed">
                <div className="feed-screen">
                  <span className="recording">● LIVE</span>
                  <div className="camera-placeholder">📹</div>
                </div>
                <div className="feed-info">
                  <strong>Camera 02</strong>
                  <span>East Sector</span>
                </div>
              </div>

              <div className="camera-feed">
                <div className="feed-screen">
                  <span className="recording">● LIVE</span>
                  <div className="camera-placeholder">📹</div>
                </div>
                <div className="feed-info">
                  <strong>Camera 03</strong>
                  <span>West Sector</span>
                </div>
              </div>

              <div className="camera-feed">
                <div className="feed-screen">
                  <span className="recording">● LIVE</span>
                  <div className="camera-placeholder">📹</div>
                </div>
                <div className="feed-info">
                  <strong>Camera 04</strong>
                  <span>South Gate</span>
                </div>
              </div>

            </div>
          </div>

          {/* Alerts */}
          <div className="panel alerts-panel">
            <div className="panel-header">
              <div>
                <h3>Recent Alerts</h3>
                <p>Latest security events</p>
              </div>
              <button onClick={() => setActivePage("alerts")}>
  View All
</button>
            </div>

            <div className="alert-item high">
              <div className="alert-symbol">!</div>
              <div>
                <strong>Unauthorized Entry</strong>
                <p>Camera 03 · West Sector</p>
                <small>2 minutes ago</small>
              </div>
            </div>

            <div className="alert-item medium">
              <div className="alert-symbol">!</div>
              <div>
                <strong>Suspicious Vehicle</strong>
                <p>Camera 01 · North Gate</p>
                <small>8 minutes ago</small>
              </div>
            </div>

            <div className="alert-item low">
              <div className="alert-symbol">i</div>
              <div>
                <strong>Person Detected</strong>
                <p>Camera 04 · South Gate</p>
                <small>15 minutes ago</small>
              </div>
            </div>

          </div>

        </section>

        {/* Bottom Section */}
        <section className="bottom-grid">

          <div className="panel">
            <div className="panel-header">
              <div>
                <h3>Detection Activity</h3>
                <p>Today's surveillance activity</p>
              </div>
            </div>

            <div className="activity-bars">
              <div style={{ height: '35%' }}></div>
              <div style={{ height: '55%' }}></div>
              <div style={{ height: '45%' }}></div>
              <div style={{ height: '75%' }}></div>
              <div style={{ height: '60%' }}></div>
              <div style={{ height: '90%' }}></div>
              <div style={{ height: '70%' }}></div>
              <div style={{ height: '82%' }}></div>
              <div style={{ height: '65%' }}></div>
              <div style={{ height: '95%' }}></div>
              <div style={{ height: '78%' }}></div>
              <div style={{ height: '88%' }}></div>
            </div>

            <div className="chart-labels">
              <span>06 AM</span>
              <span>09 AM</span>
              <span>12 PM</span>
              <span>03 PM</span>
              <span>06 PM</span>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h3>System Health</h3>
                <p>Current infrastructure status</p>
              </div>
            </div>

            <div className="health-row">
              <span>Camera Network</span>
              <strong>98%</strong>
            </div>

            <div className="progress">
              <div className="progress-fill" style={{ width: '98%' }}></div>
            </div>

            <div className="health-row">
              <span>Video Processing</span>
              <strong>94%</strong>
            </div>

            <div className="progress">
              <div className="progress-fill" style={{ width: '94%' }}></div>
            </div>

            <div className="health-row">
              <span>AI Analytics</span>
              <strong>96%</strong>
            </div>

            <div className="progress">
              <div className="progress-fill" style={{ width: '96%' }}></div>
            </div>
          </div>

       </section>
  {/* Event History */}
<section className="panel event-dashboard-panel">

  <div className="panel-header">
    <div>
      <h3>Recent Event History</h3>
      <p>Latest surveillance events</p>
    </div>

    <button onClick={() => setActivePage("events")}>
      View All
    </button>
  </div>

  <div className="dashboard-event-list">

    <div className="dashboard-event-row">
      <div>
        <strong>Unauthorized Entry</strong>
        <span>CAM-03 · West Sector</span>
      </div>
      <div>
        <strong>14:32</strong>
        <span className="event-pending">Pending</span>
      </div>
    </div>

    <div className="dashboard-event-row">
      <div>
        <strong>Vehicle Detected</strong>
        <span>CAM-01 · North Gate</span>
      </div>
      <div>
        <strong>14:18</strong>
        <span className="event-reviewed">Reviewed</span>
      </div>
    </div>

    <div className="dashboard-event-row">
      <div>
        <strong>Person Detected</strong>
        <span>CAM-04 · South Gate</span>
      </div>
      <div>
        <strong>13:55</strong>
        <span className="event-pending">Pending</span>
      </div>
    </div>

    <div className="dashboard-event-row">
      <div>
        <strong>Virtual Fence Intrusion</strong>
        <span>CAM-07 · Border Fence</span>
      </div>
      <div>
        <strong>13:41</strong>
        <span className="event-pending">Pending</span>
      </div>
    </div>

  </div>

</section>
 </>
)}
<div className="dashboard-footer">
  <span>IBVAP • Border Surveillance System</span>
  <span>System Status: Operational</span>
  <span>Frontend Prototype • SIH 2026</span>
</div>

      </main>
    </div>
  );
}

export default App;