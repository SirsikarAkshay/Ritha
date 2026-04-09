// src/components/Logo.jsx
// Theme-aware logo that swaps between black/white variants.
// Reads the current theme from ThemeContext.
import { useTheme } from '../hooks/useTheme.jsx'

export default function Logo({ className = '', style = {}, alt = 'Arokah' }) {
  const { theme } = useTheme()
  // Per request: dark mode → arokah_black.jpeg, light mode → arokah_white.jpeg
  const src = theme === 'dark' ? '/arokah_black.jpeg' : '/arokah_white.jpeg'

  // JPEGs can't be transparent. Use mix-blend-mode to drop the background:
  //   - 'screen' in dark mode makes black/near-black pixels transparent,
  //     leaving the bright logo art visible on the dark sidebar.
  //   - 'multiply' in light mode makes white/near-white pixels transparent,
  //     leaving the dark logo art visible on the light sidebar.
  const blend = theme === 'dark' ? 'screen' : 'multiply'

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={{ mixBlendMode: blend, ...style }}
      onError={e => console.error('[Logo] failed to load:', e.currentTarget.src)}
    />
  )
}
