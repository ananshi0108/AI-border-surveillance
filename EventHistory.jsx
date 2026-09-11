function EventHistory() {
  const events = [
    {
      id: "EVT-001",
      type: "Unauthorized Entry",
      camera: "CAM-03",
      location: "West Sector",
      time: "Today, 14:32",
      status: "Reviewed",
    },
    {
      id: "EVT-002",
      type: "Vehicle Detected",
      camera: "CAM-01",
      location: "North Gate",
      time: "Today, 14:18",
      status: "Reviewed",
    },
    {
      id: "EVT-003",
      type: "Person Detected",
      camera: "CAM-04",
      location: "South Gate",
      time: "Today, 13:55",
      status: "Pending",
    },
    {
      id: "EVT-004",
      type: "Virtual Fence Intrusion",
      camera: "CAM-07",
      location: "Border Fence",
      time: "Today, 13:41",
      status: "Pending",
    },
    {
      id: "EVT-005",
      type: "Night Movement",
      camera: "CAM-12",
      location: "Main Road",
      time: "Today, 12:26",
      status: "Reviewed",
    },
  ];

  return (
    <div className="event-history-page">

      <div className="page-heading">
        <div>
          <p className="breadcrumb">Dashboard / Event History</p>
          <h1>Event History</h1>
          <p>Search and review previously detected security events</p>
        </div>
      </div>

      <div className="event-table-card">

        <table className="event-table">

          <thead>
            <tr>
              <th>Event ID</th>
              <th>Event Type</th>
              <th>Camera</th>
              <th>Location</th>
              <th>Time</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{event.id}</td>
                <td>{event.type}</td>
                <td>{event.camera}</td>
                <td>{event.location}</td>
                <td>{event.time}</td>
                <td>
                  <span
                    className={
                      event.status === "Pending"
                        ? "event-pending"
                        : "event-reviewed"
                    }
                  >
                    {event.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>

        </table>

      </div>

    </div>
  );
}

export default EventHistory;