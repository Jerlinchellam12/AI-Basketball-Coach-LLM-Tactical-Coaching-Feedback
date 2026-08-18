import "./Timeline.css";

function fmt(t) {
  const m = Math.floor(t / 60);
  const s = (t % 60).toFixed(1).padStart(4, "0");
  return `${m}:${s}`;
}

export default function Timeline({ duration, currentTime, momentStart, momentEnd, onSeek }) {
  if (!duration) return <div className="timeline timeline-empty" />;

  const pct = (t) => `${(t / duration) * 100}%`;

  const handleClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    onSeek(frac * duration);
  };

  const ticks = 10;

  return (
    <div className="timeline">
      <div className="timeline-track" onClick={handleClick}>
        <div
          className="timeline-moment-range"
          style={{ left: pct(momentStart), width: pct(momentEnd - momentStart) }}
        />
        {Array.from({ length: ticks + 1 }).map((_, i) => (
          <div key={i} className="timeline-tick" style={{ left: `${(i / ticks) * 100}%` }} />
        ))}
        <div className="timeline-playhead" style={{ left: pct(currentTime) }} />
      </div>
      <div className="timeline-labels">
        <span className="mono tabular">{fmt(currentTime)}</span>
        <span className="mono tabular timeline-total">{fmt(duration)}</span>
      </div>
    </div>
  );
}
