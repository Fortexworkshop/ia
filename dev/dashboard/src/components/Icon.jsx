// Icônes inline (aucune requête réseau). Toujours décoratives : le sens est porté par le texte voisin.
const PATHS = {
  overview: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
  alarm: 'M12 2 1 21h22L12 2zm0 6 .01 0M11 10h2v5h-2zm0 7h2v2h-2z',
  critical: 'M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86L7.86 2zM11 7v6h2V7h-2zm0 8v2h2v-2h-2z',
  warning: 'M12 2 1 21h22L12 2zm-1 7h2v6h-2V9zm0 8h2v2h-2v-2z',
  check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z',
  shield: 'M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3zm-1 14-4-4 1.4-1.4L11 13.2l5.6-5.6L18 9l-7 7z',
  unlink: 'M17 7h-4v2h4a3 3 0 0 1 0 6h-4v2h4a5 5 0 0 0 0-10zM7 15a3 3 0 0 1 0-6h4V7H7a5 5 0 0 0 0 10h4v-2H7zM3.4 2 2 3.4 20.6 22l1.4-1.4L3.4 2z',
  people: 'M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm0 2c-2.3 0-7 1.2-7 3.5V19h14v-2.5C15 14.2 10.3 13 8 13zm8 0c-.3 0-.6 0-1 .1 1.2.8 2 2 2 3.4V19h6v-2.5c0-2.3-4.7-3.5-7-3.5z',
  presence: 'M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm0 16H5V8h14v11zM10.6 17.4 7 13.8l1.4-1.4 2.2 2.2 5-5L17 11l-6.4 6.4z',
  camera: 'M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11l-4 4z',
  sun: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM11 1h2v3h-2zm0 19h2v3h-2zM1 11h3v2H1zm19 0h3v2h-3zM4.2 5.6l1.4-1.4 2.1 2.1-1.4 1.4zm12.1 12.1 1.4-1.4 2.1 2.1-1.4 1.4zM4.2 18.4l2.1-2.1 1.4 1.4-2.1 2.1zM16.3 6.3l2.1-2.1 1.4 1.4-2.1 2.1z',
  moon: 'M12.3 2a10 10 0 1 0 9.7 12.4A8 8 0 0 1 12.3 2z',
  contrast: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18V4a8 8 0 0 1 0 16z',
  mute: 'M16.5 12A4.5 4.5 0 0 0 14 8v2.2l2.5 2.5V12zM19 12c0 .9-.2 1.8-.5 2.6l1.5 1.5A8.8 8.8 0 0 0 21 12c0-4.3-3-7.9-7-8.8v2.1c2.9.9 5 3.5 5 6.7zM4.3 3 3 4.3 7.7 9H3v6h4l5 5v-6.7l4.3 4.2c-.7.5-1.4.9-2.3 1.2v2.1c1.4-.3 2.6-1 3.7-1.8L19.7 21 21 19.7 4.3 3zM12 4 9.9 6.1 12 8.2V4z',
  info: 'M11 7h2v2h-2zm0 4h2v6h-2zm1-9a10 10 0 1 0 0 20 10 10 0 0 0 0-20z',
  flask: 'M7 2v2h1v6.4L3.6 18.1A2 2 0 0 0 5.3 21h13.4a2 2 0 0 0 1.7-2.9L16 10.4V4h1V2H7zm3 2h4v7l2.3 4H7.7L10 11V4z',
}

export default function Icon({ name, ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false" {...props}>
      <path d={PATHS[name]} fillRule="evenodd" />
    </svg>
  )
}

// Logo FORTEX : un bastion (vue en plan d'un fort à redans) entourant un capteur.
export function Logo(props) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false" {...props}>
      <path
        d="M16 2 6 6v4H2l4 6-4 6h4v4l10 4 10-4v-4h4l-4-6 4-6h-4V6L16 2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="4" fill="var(--accent)" />
      <circle cx="16" cy="16" r="8" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="3 3" />
    </svg>
  )
}
