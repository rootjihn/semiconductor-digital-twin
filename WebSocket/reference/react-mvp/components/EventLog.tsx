import type { EventItem } from '../lib/types';

export function EventLog({ events, onClear }: { events: EventItem[]; onClear: () => void }) {
  return (
    <section className="panel event-panel">
      <div className="panel-heading row-between">
        <div>
          <p className="eyebrow">Events</p>
          <h2>이벤트 로그</h2>
        </div>
        <button className="secondary small" onClick={onClear}>Clear</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Time</th><th>Severity</th><th>Source</th><th>Message</th></tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={`${event.timestamp}-${index}`}>
                <td>{event.timestamp}</td><td>{event.severity}</td><td>{event.source}</td><td>{event.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
