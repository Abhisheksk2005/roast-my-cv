export function BurningCapIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className}>
      <path d="M32 28L8 38L32 48L56 38L32 28Z" fill="currentColor" opacity="0.9" />
      <path d="M48 41V52L32 58L16 52V41L32 48L48 41Z" fill="currentColor" opacity="0.7" />
      <path d="M52 38V50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="52" cy="52" r="2.5" fill="currentColor" />
      <path d="M24 26C24 20 28 16 30 12C32 16 29 20 32 22C35 20 33 14 36 10C38 14 42 18 40 26" stroke="#E63946" strokeWidth="2" fill="#E63946" fillOpacity="0.3" strokeLinecap="round" />
      <path d="M28 24C28 20 31 18 32 15C33 18 34 20 36 24" stroke="#F5A623" strokeWidth="1.5" fill="#F5A623" fillOpacity="0.4" strokeLinecap="round" />
    </svg>
  );
}

export function MoneyBurningIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className}>
      <rect x="10" y="20" width="44" height="24" rx="3" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.05" />
      <path d="M32 24V40" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M27 27C27 25 29 24 32 24C35 24 37 25.5 37 27.5C37 29.5 35 30 32 31C29 32 27 32.5 27 35C27 37 29 38.5 32 39C35 39 37 38 37 36" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M14 20C14 14 18 12 20 8C22 12 19 16 22 18" stroke="#E63946" strokeWidth="2" fill="#E63946" fillOpacity="0.2" strokeLinecap="round" />
      <path d="M42 20C42 14 46 12 48 8C50 12 47 16 50 18" stroke="#F5A623" strokeWidth="2" fill="#F5A623" fillOpacity="0.2" strokeLinecap="round" />
    </svg>
  );
}

export function CrackingDiplomaIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className}>
      <rect x="12" y="16" width="40" height="32" rx="2" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.05" />
      <path d="M18 24H46" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <path d="M18 30H40" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <path d="M18 36H36" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <path d="M30 14L33 22L28 28L34 34L30 42L33 50" stroke="#E63946" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function GavelIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className}>
      <rect x="18" y="14" width="28" height="12" rx="3" transform="rotate(-30 32 20)" fill="currentColor" opacity="0.8" />
      <path d="M32 28L44 52" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M16 32L12 36" stroke="#F5A623" strokeWidth="2" strokeLinecap="round" />
      <path d="M20 36L14 42" stroke="#F5A623" strokeWidth="2" strokeLinecap="round" />
      <ellipse cx="20" cy="50" rx="12" ry="4" fill="currentColor" opacity="0.3" />
    </svg>
  );
}

export function MicIcon({ className = "", size = 24 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={className}>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" fill="none" />
      <path d="M12 17v4M8 21h8" />
    </svg>
  );
}

export function ChartDownIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className}>
      <path d="M12 12V52H56" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 20L28 28L36 24L52 48" stroke="#E63946" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M48 42L52 48L46 46" stroke="#E63946" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function DonaldLogo({ className = "" }: { className?: string }) {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none" className={className}>
      <path d="M8 4H18C24.627 4 30 9.373 30 16C30 22.627 24.627 28 18 28H8V4Z" stroke="currentColor" strokeWidth="2.5" fill="none" />
      <path d="M8 4V28" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M14 2L16 10L13 16L17 22L14 30" stroke="#F5A623" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
