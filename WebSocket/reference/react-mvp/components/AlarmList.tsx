import type { EventItem } from '../lib/types';

export function AlarmList({ alarms }: { alarms: EventItem[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <p className="eyebrow">Alarms</p>
        <h2>알람</h2>
      </div>
      <div className="alarm-list">
        {alarms.length === 0 ? <p className="hint">활성 알람 없음</p> : alarms.map((alarm, index) => (
          <div className={`alarm-item ${alarm.severity.toLowerCase()}`} key={`${alarm.message}-${index}`}>
            <strong>{alarm.severity}</strong> · {alarm.source}<br />
            <span>{alarm.message}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
