const commands = [
  ['process.start', 'Start', 'primary'],
  ['process.pause', 'Pause', 'primary'],
  ['process.stop', 'Stop', 'warning'],
  ['process.reset_error', 'Reset Error', 'primary'],
  ['robot.home', 'Home Robot', 'secondary'],
  ['system.refresh', 'Refresh', 'secondary'],
] as const;

export function ControlPanel({ onCommand }: { onCommand: (command: string) => void }) {
  return (
    <section className="panel danger-panel">
      <div className="panel-heading">
        <p className="eyebrow">Control</p>
        <h2>제어 패널</h2>
      </div>
      <div className="button-grid">
        {commands.map(([command, label, tone]) => (
          <button className={tone} key={command} onClick={() => onCommand(command)}>
            {label}
          </button>
        ))}
      </div>
      <p className="hint">MVP1: 실제 장비를 제어하지 않고 command payload와 event log만 생성합니다.</p>
    </section>
  );
}
