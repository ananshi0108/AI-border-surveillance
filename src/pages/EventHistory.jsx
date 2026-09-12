import { useEffect, useState } from "react";

function EventHistory() {
  const [events, setEvents] = useState([]);

useEffect(() => {
  const fetchEvents = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/alerts/"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch events");
      }

      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error("Error fetching events:", error);
    }
  };

  fetchEvents();
}, []);

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
               <td>EVT-{String(event.id).padStart(3, "0")}</td>

               <td>{event.alert_type}</td>

               <td>
                 CAM-{String(event.camera_id).padStart(2, "0")}
               </td>

               <td>
                 Zone {event.zone_id}
               </td>

               <td>
                 {new Date(event.timestamp).toLocaleString()}
               </td>

               <td>
                 <span
                   className={
                    event.status === "NEW"
                    ? "event-pending"
                    : "event-reviewed"
                    }
                  >
                    {event.status === "NEW" ? "Pending" : "Reviewed"}
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