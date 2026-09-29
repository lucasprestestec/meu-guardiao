/** Ilustração de apoio no lugar das fotos dos mockups (sem banco de imagens). */
export function Escudo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 360 320" className={className} role="img" aria-label="Escudo de proteção">
      <defs>
        <linearGradient id="esc" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4d8cf5" />
          <stop offset="1" stopColor="#1560e8" />
        </linearGradient>
        <linearGradient id="fol" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2fb59f" />
          <stop offset="1" stopColor="#0c8f88" />
        </linearGradient>
      </defs>
      <rect x="150" y="30" width="170" height="230" rx="18" fill="#fff" stroke="#dbe7f6" strokeWidth="2" />
      <rect x="172" y="56" width="70" height="8" rx="4" fill="#dbe7f6" />
      <rect x="172" y="76" width="46" height="8" rx="4" fill="#e9f0fa" />
      <rect x="248" y="150" width="16" height="60" rx="5" fill="#bcd3f6" />
      <rect x="272" y="126" width="16" height="84" rx="5" fill="#8db6f3" />
      <rect x="296" y="100" width="16" height="110" rx="5" fill="#5f9bf0" />
      <path d="M92 250c-28-30-30-84 0-130 22 30 30 84 0 130z" fill="url(#fol)" />
      <path d="M86 260c-40-6-62-42-52-84 34 6 58 42 52 84z" fill="#3aa596" opacity=".8" />
      <path d="M180 92l78 26v64c0 46-32 72-78 92-46-20-78-46-78-92v-64z" fill="url(#esc)" />
      <path d="M180 92l78 26v64c0 46-32 72-78 92z" fill="#0f4cc0" opacity=".18" />
      <path d="M146 186l26 26 48-56" fill="none" stroke="#fff" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="120" y="262" width="150" height="26" rx="13" fill="#e4edf9" />
    </svg>
  );
}
