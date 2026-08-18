import { useRef } from "react";

// Lightweight pointer-driven 3D tilt (CSS transform only, no 3D library) -
// gives a real interactive-3D feel on hover without the weight/complexity
// of a WebGL scene, which isn't warranted for a data comparison card grid.
export default function useTilt(maxDeg = 6) {
  const ref = useRef(null);

  const onMouseMove = (e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    el.style.transform = `perspective(900px) rotateY(${px * maxDeg * 2}deg) rotateX(${-py * maxDeg * 2}deg) translateZ(4px)`;
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "perspective(900px) rotateY(0deg) rotateX(0deg) translateZ(0px)";
  };

  return { ref, onMouseMove, onMouseLeave };
}
