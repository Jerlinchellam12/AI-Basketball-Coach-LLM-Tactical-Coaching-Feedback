import "./ClipSelector.css";

export default function ClipSelector({ clips, selected, onSelect }) {
  return (
    <nav className="clip-selector">
      {clips.map((id, i) => (
        <button
          key={id}
          className={`clip-tab ${id === selected ? "active" : ""}`}
          onClick={() => onSelect(id)}
        >
          {`CLIP ${i + 1}`}
        </button>
      ))}
    </nav>
  );
}
