interface StatusCardProps {
  title: string;
  value: string;
  detail: string;
  tone?: 'ok' | 'warn' | 'error' | 'mock';
}

export function StatusCard({ title, value, detail, tone = 'mock' }: StatusCardProps) {
  return (
    <article className={`panel status-card ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
