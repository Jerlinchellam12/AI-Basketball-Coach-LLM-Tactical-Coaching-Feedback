import { useEffect, useState } from "react";
import ClipSelector from "./components/ClipSelector";
import VideoStage from "./components/VideoStage";
import MomentInfo from "./components/MomentInfo";
import RepresentationGrid from "./components/RepresentationGrid";
import BasketballIcon from "./components/BasketballIcon";
import CourtLineArt from "./components/CourtLineArt";
import "./App.css";

export default function App() {
  const [manifest, setManifest] = useState(null);
  const [clipId, setClipId] = useState(null);
  const [clipData, setClipData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/data/manifest.json")
      .then((r) => r.json())
      .then((m) => {
        setManifest(m);
        if (m.clips?.length) setClipId(m.clips[0]);
      })
      .catch((e) => setError(`Failed to load manifest.json: ${e.message}`));
  }, []);

  useEffect(() => {
    if (!clipId) return;
    setClipData(null);
    fetch(`/data/${clipId}.json`)
      .then((r) => r.json())
      .then(setClipData)
      .catch((e) => setError(`Failed to load ${clipId}.json: ${e.message}`));
  }, [clipId]);

  return (
    <div className="app">
      <header className="app-header">
        <CourtLineArt />
        <div className="brand">
          <BasketballIcon size={30} spin />
          AI BASKETBALL COACH
        </div>
        <div className="brand-sub">representation comparison</div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {manifest && (
        <ClipSelector clips={manifest.clips} selected={clipId} onSelect={setClipId} />
      )}

      {clipData && (
        <main className="app-main">
          <div className="stage-col">
            <VideoStage clip={clipData} />
            <MomentInfo clip={clipData} />
          </div>
          <RepresentationGrid clip={clipData} />
        </main>
      )}

      {!clipData && !error && <div className="loading">Loading...</div>}
    </div>
  );
}
