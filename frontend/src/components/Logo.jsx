// src/components/Logo.jsx
// Theme-aware logo that swaps between black/white variants.
// Reads the current theme from ThemeContext.
import { useTheme } from '../hooks/useTheme.jsx'

// Bumped whenever the public/ritha_*.jpeg files change so browsers refetch
// instead of serving a stale cached copy under the unchanged filename.
const LOGO_VERSION = '3'

export default function Logo({ className = '', style = {}, alt = 'Ritha' }) {
  const { theme } = useTheme()
  // Per request: dark mode → ritha_black.jpeg, light mode → ritha_white.jpeg
  const file = theme === 'dark' ? '/ritha_black.jpeg' : '/ritha_white.jpeg'
  const src  = `${file}?v=${LOGO_VERSION}`

  // JPEGs can't be transparent. Use mix-blend-mode to drop the background:
  //   - 'screen' in dark mode makes black/near-black pixels transparent,
  //     leaving the bright logo art visible on the dark sidebar.
  //   - 'multiply' in light mode makes white/near-white pixels transparent,
  //     leaving the dark logo art visible on the light sidebar.
  // The contrast/brightness filter crushes JPEG compression noise around the
  // logo edges to true black/white so the blend mode produces a clean cutout
  // instead of a faint halo on the sidebar background.
  const blend  = theme === 'dark' ? 'screen' : 'multiply'
  const filter = theme === 'dark'
    ? 'brightness(1.05) contrast(1.25)'
    : 'brightness(0.97) contrast(1.20)'

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={{ mixBlendMode: blend, filter, ...style }}
      onError={e => console.error('[Logo] failed to load:', e.currentTarget.src)}
    />
  )
}
