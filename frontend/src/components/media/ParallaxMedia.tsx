import { motion, useScroll, useSpring, useTransform } from 'motion/react'
import { useRef, type ReactNode } from 'react'
import { useIsMobile, usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { SCROLL_SPRING } from '../../lib/motion'

const MAX_DESKTOP = 48
const MOBILE_FACTOR = 0.3

/**
 * Moves its child slightly slower than the page. The wrapper reserves the
 * full travel distance as padding, so the media can never overlap neighbours.
 * Motion values drive the transform — no React state updates on scroll.
 */
export function ParallaxMedia({ strength = 32, children }: { strength?: number; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()
  const mobile = useIsMobile()
  const clamped = Math.min(Math.max(strength, 0), MAX_DESKTOP)
  const travel = reduced ? 0 : Math.round(clamped * (mobile ? MOBILE_FACTOR : 1))

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const progress = useSpring(scrollYProgress, SCROLL_SPRING)
  const y = useTransform(progress, [0, 1], [-travel, travel], { clamp: true })

  return (
    <div ref={ref} style={{ paddingBlock: travel }}>
      <motion.div style={{ y: travel ? y : 0 }} data-print="static">
        {children}
      </motion.div>
    </div>
  )
}
