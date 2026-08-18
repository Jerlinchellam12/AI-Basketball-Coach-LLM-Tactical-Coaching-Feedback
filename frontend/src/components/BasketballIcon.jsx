export default function BasketballIcon({ size = 28, className = "", spin = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={`basketball-icon ${spin ? "basketball-icon-spin" : ""} ${className}`}
    >
      <circle cx="16" cy="16" r="15" fill="var(--orange)" stroke="var(--ink)" strokeWidth="1.4" />
      <path d="M16 1 L16 31 M1 16 L31 16" stroke="var(--ink)" strokeWidth="1.4" fill="none" />
      <path d="M4.2 6.2 C 11 12, 11 20, 4.2 25.8" stroke="var(--ink)" strokeWidth="1.4" fill="none" />
      <path d="M27.8 6.2 C 21 12, 21 20, 27.8 25.8" stroke="var(--ink)" strokeWidth="1.4" fill="none" />
    </svg>
  );
}
