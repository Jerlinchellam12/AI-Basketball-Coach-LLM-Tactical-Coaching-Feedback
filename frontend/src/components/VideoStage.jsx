import { useEffect, useRef, useState } from "react";
import Timeline from "./Timeline";
import useTilt from "../hooks/useTilt";
import "./VideoStage.css";

const VIEWS = [
  { key: "original", label: "Original" },
  { key: "overlay_2d", label: "2D Skeleton" },
  { key: "overlay_3d", label: "3D Skeleton" },
];

export default function VideoStage({ clip }) {
  const videoRef = useRef(null);
  const tilt = useTilt(3);
  const [view, setView] = useState("original");
  const [loop, setLoop] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const src =
    view === "original" ? clip.video_src : view === "overlay_2d" ? clip.overlay_2d_src : clip.overlay_3d_src;

  const lastClipRef = useRef(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const clipChanged = lastClipRef.current !== clip.clip_id;
    lastClipRef.current = clip.clip_id;

    if (clipChanged) {
      // key={clip.clip_id} on the <video> below already remounts a fresh
      // element for a new clip, which naturally loads its initial
      // <source> + autoPlay. Calling load() again here raced that natural
      // load and left the element stuck at readyState 0 - just listen.
      // Normal playback (clip selection, view toggle) plays the whole
      // clip start to end, same as any other video - it is NOT the same
      // thing as "Jump to moment". Looping moment_start_sec..moment_end_sec
      // only happens when the user explicitly clicks "Jump to moment".
      setLoop(false);
      const onLoaded = () => {
        setDuration(v.duration || 0);
      };
      v.addEventListener("loadedmetadata", onLoaded, { once: true });
      return () => v.removeEventListener("loadedmetadata", onLoaded);
    }

    // Same clip, different view (Original/2D/3D toggle) - the element
    // persists, so it needs an explicit load() to pick up the new
    // <source src>, since React doesn't touch the DOM src attribute here.
    const t = v.currentTime;
    v.load();
    const onLoaded = () => {
      v.currentTime = Math.min(t, v.duration || 0);
      setDuration(v.duration || 0);
      v.play();
    };
    v.addEventListener("loadedmetadata", onLoaded, { once: true });
    return () => v.removeEventListener("loadedmetadata", onLoaded);
  }, [view, clip.clip_id]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onTime = () => {
      setCurrentTime(v.currentTime);
      if (loop && v.currentTime >= clip.moment_end_sec) {
        v.currentTime = clip.moment_start_sec;
        v.play();
      }
    };
    v.addEventListener("timeupdate", onTime);
    return () => v.removeEventListener("timeupdate", onTime);
  }, [loop, clip.moment_start_sec, clip.moment_end_sec]);

  const seekToMoment = () => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = clip.moment_start_sec;
    v.play();
    setLoop(true);
  };

  return (
    <div className="video-stage">
      <div className="video-frame" ref={tilt.ref} onMouseMove={tilt.onMouseMove} onMouseLeave={tilt.onMouseLeave}>
        <video ref={videoRef} key={clip.clip_id} controls autoPlay muted playsInline>
          <source src={src} type="video/mp4" />
        </video>
      </div>

      <div className="view-toggle">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            className={view === v.key ? "active" : ""}
            onClick={() => setView(v.key)}
          >
            {v.label}
          </button>
        ))}
      </div>

      <Timeline
        duration={duration}
        currentTime={currentTime}
        momentStart={clip.moment_start_sec}
        momentEnd={clip.moment_end_sec}
        onSeek={(t) => {
          if (videoRef.current) videoRef.current.currentTime = t;
        }}
      />

      <div className="stage-actions">
        <button className={`action-btn ${loop ? "active" : ""}`} onClick={seekToMoment}>
          {loop ? "Looping moment" : "Jump to moment"}
        </button>
      </div>
    </div>
  );
}
