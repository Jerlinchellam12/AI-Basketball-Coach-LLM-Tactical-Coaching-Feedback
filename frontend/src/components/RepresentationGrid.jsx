import useTilt from "../hooks/useTilt";
import "./RepresentationGrid.css";

const LABELS = {
  raw_2d: "Raw 2D Pose",
  raw_3d: "Raw 3D Pose",
  json_summary: "Structured JSON Summary",
  nl_description: "Natural Language",
};

export default function RepresentationGrid({ clip }) {
  const order = ["raw_2d", "raw_3d", "json_summary", "nl_description"];
  return (
    <div className="repr-grid">
      {order.map((key) => (
        <RepresentationCard
          key={key}
          repKey={key}
          label={LABELS[key]}
          data={clip.representations[key]}
          feedback={clip.feedback[key]}
        />
      ))}
    </div>
  );
}

function RepresentationCard({ repKey, label, data, feedback }) {
  const isRaw = repKey === "raw_2d" || repKey === "raw_3d";
  const tilt = useTilt(4);
  return (
    <div className="repr-card" ref={tilt.ref} onMouseMove={tilt.onMouseMove} onMouseLeave={tilt.onMouseLeave}>
      <div className="repr-card-header">
        <span className="repr-label">{label}</span>
        {isRaw && (
          <span className="repr-meta mono tabular">{data.frame_count} frames sampled</span>
        )}
      </div>

      <details className="repr-data">
        <summary>view input data</summary>
        <pre className="mono">
          {repKey === "nl_description"
            ? data
            : JSON.stringify(isRaw ? data.preview : data, null, 2)}
        </pre>
      </details>

      <div className="repr-feedback">
        <div className="identified-move">
          <span className={`match-dot ${feedback.move_type_match ? "match" : "no-match"}`} />
          <span className="identified-move-text">"{feedback.identified_move}"</span>
        </div>

        <p className="positive-observation">{feedback.positive_observation}</p>

        <ol className="alternative-moves">
          {feedback.alternative_moves.map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}
