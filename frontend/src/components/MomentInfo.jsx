import "./MomentInfo.css";

export default function MomentInfo({ clip }) {
  return (
    <div className="moment-info">
      <div className="moment-players">
        <span className="player-chip attacker">{clip.attacker_label} · attacker</span>
        <span className="player-chip defender">{clip.defender_label} · defender</span>
      </div>
      <div className="moment-badges">
        <Badge label="outcome" value={clip.outcome.replaceAll("_", " ")} />
        <Badge label="contested" value={clip.contested} />
        <Badge label="location" value={clip.shot_location.replaceAll("_", " ")} />
        <Badge label="actual move" value={clip.actual_move_type.replaceAll("_", " ")} highlight />
      </div>
    </div>
  );
}

function Badge({ label, value, highlight }) {
  return (
    <div className={`badge ${highlight ? "badge-highlight" : ""}`}>
      <span className="badge-label">{label}</span>
      <span className="badge-value">{value}</span>
    </div>
  );
}
