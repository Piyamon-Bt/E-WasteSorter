import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { EASE_FLOW, SWAP } from '../../lib/motion'

interface FadeSwapProps {
  /** When this changes, the content re-enters with a soft fade and rise. */
  swapKey: string
  children: ReactNode
  className?: string
}

/**
 * Gentle entrance for content that changes with workflow state.
 * Note: changing `swapKey` remounts the children, so only use it around
 * content whose local state may safely reset.
 */
export function FadeSwap({ swapKey, children, className }: FadeSwapProps) {
  const reduced = usePrefersReducedMotion()
  return (
    <motion.div
      key={swapKey}
      data-print="static"
      className={className}
      initial={reduced ? false : { opacity: 0, y: SWAP.distance }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: SWAP.duration, ease: EASE_FLOW }}
    >
      {children}
    </motion.div>
  )
}
