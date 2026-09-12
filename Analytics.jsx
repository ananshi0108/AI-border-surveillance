import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function Analytics() {
  const activityData = [
    { time: "06 AM", persons: 18, vehicles: 10 },
    { time: "08 AM", persons: 25, vehicles: 15 },
    { time: "10 AM", persons: 32, vehicles: 20 },
    { time: "12 PM", persons: 28, vehicles: 18 },
    { time: "02 PM", persons: 40, vehicles: 24 },
    { time: "04 PM", persons: 35, vehicles: 22 },
    { time: "06 PM", persons: 45, vehicles: 30 },
  ];

  const alertData = [
    { type: "Entry", count: 12 },
    { type: "Vehicle", count: 8 },
    { type: "Fence", count: 6 },
    { type: "Night", count: 4 },
  ];

  return (
    <div className="analytics-page">

      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Analytics</p>
          <h1>Surveillance Analytics</h1>
          <p>Analyze border surveillance and detection activity</p>
        </div>
      </div>

      <div className="analytics-grid">

        <div className="analytics-card">
          <h3>Detection Activity</h3>
          <p>Persons and vehicles detected today</p>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />

                <Line
                  type="monotone"
                  dataKey="persons"
                  stroke="#4ade80"
                  strokeWidth={3}
                />

                <Line
                  type="monotone"
                  dataKey="vehicles"
                  stroke="#60a5fa"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="analytics-card">
          <h3>Security Events</h3>
          <p>Events detected by category</p>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={alertData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="#f59e0b"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
}

export default Analytics;