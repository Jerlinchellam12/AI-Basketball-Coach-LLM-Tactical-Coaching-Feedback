import "./CourtLineArt.css";

// Coach's-diagram-style line art (dashed trajectory arcs + a travelling
// ball dot) as an animated background motif - echoes the shot-arc overlay
// language from the reference sites, and ties visually into the fact that
// this app itself draws lines (pose skeletons) over basketball footage.
export default function CourtLineArt() {
  return (
    <svg className="court-line-art" viewBox="0 0 1200 260" preserveAspectRatio="none" aria-hidden="true">
      <path
        className="court-arc court-arc-1"
        d="M -50 220 Q 250 -40, 550 180 T 1250 120"
        fill="none"
      />
      <path
        className="court-arc court-arc-2"
        d="M -50 60 Q 300 260, 650 40 T 1250 200"
        fill="none"
      />
      <circle className="court-ball" r="5" fill="var(--orange)">
        <animateMotion
          dur="9s"
          repeatCount="indefinite"
          path="M -50 220 Q 250 -40, 550 180 T 1250 120"
        />
      </circle>
    </svg>
  );
}
