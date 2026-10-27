import { motion, useScroll, useSpring, useTransform } from 'motion/react'
import { useRef } from 'react'
import { useIsMobile, usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { SCROLL_SPRING } from '../../lib/motion'

interface SectionHeadingProps {
  id: string
  number: string
  heading: string
  intro: string
}

/** Max vertical travel (px) per layer on desktop. Deeper layers move more, so they read as further away. */
const TRAVEL = { number: 64, heading: 14, intro: 6 }
const MOBILE_FACTOR = 0.4

/**
 * Section heading with layered typographic parallax:
 * a large faint section number behind, then the heading, then the intro.
 * Only editorial text moves — controls below stay stationary.
 * Motion values drive transforms (no React re-renders on scroll).
 */
export function SectionHeading({ id, number, heading, intro }: SectionHeadingProps) {
  const ref = useRef<HTMLElement>(null)
  const reduced = usePrefersReducedMotion()
  const mobile = useIsMobile()
  const k = reduced ? 0 : mobile ? MOBILE_FACTOR : 1

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  // Smoothed progress: layers glide into place instead of locking to each scroll tick.
  const progress = useSpring(scrollYProgress, SCROLL_SPRING)
  const range = (t: number) => [-t * k, t * k]
  const numberY = useTransform(progress, [0, 1], range(TRAVEL.number))
  const headingY = useTransform(progress, [0, 1], range(TRAVEL.heading))
  const introY = useTransform(progress, [0, 1], range(TRAVEL.intro))

  return (
    <header ref={ref} className="relative mb-10">
      <motion.span
        aria-hidden
        data-print="hide"
        style={{ y: numberY }}
        className="pointer-events-none absolute -top-10 -left-1 z-0 select-none text-[clamp(6rem,4rem+8vw,11rem)] leading-none font-semibold tracking-[-0.04em] text-[#eeeeee] tabular-nums md:-top-12"
      >
        {number}
      </motion.span>

      <div className="relative z-10">
        <p className="mb-4 text-[13px] font-medium tracking-[0.04em] text-muted tabular-nums">
          <span className="sr-only">Step </span>
          {number}
        </p>
        <motion.h2
          id={`${id}-heading`}
          tabIndex={-1}
          data-section-heading
          data-print="static"
          style={{ y: headingY }}
          className="heading-fluid text-ink"
        >
          {heading}
        </motion.h2>
        <motion.p
          data-print="static"
          style={{ y: introY }}
          className="prose-width mt-5 text-[17px] leading-[1.65] text-muted"
        >
          {intro}
        </motion.p>
      </div>
    </header>
  )
}
