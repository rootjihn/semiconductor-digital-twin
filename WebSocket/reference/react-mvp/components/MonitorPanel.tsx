interface MonitorPanelProps {
  eyebrow?: string;
  title: string;
  rows: Array<[string, string | number | boolean]>;
}

export function MonitorPanel({ eyebrow = 'Monitor', title, rows }: MonitorPanelProps) {
  return (
    <article className="panel">
      <div className="panel-heading">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {rows.map(([label, value]) => (
        <div className="kv" key={label}>
          <span>{label}</span>
          <strong>{String(value)}</strong>
        </div>
      ))}
    </article>
  );
}
