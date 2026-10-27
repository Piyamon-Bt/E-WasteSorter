import { Check } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { sections } from '../../content/sections'
import { usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { EASE_FLOW } from '../../lib/motion'
import { useAssessment } from '../../state/AssessmentContext'
import { selectCompleted } from '../../state/selectors'

/** Distance from the rail to the left edge of each section's text column. */
const GUTTER = 28
/** Vertical offset of the node from the top of the section header (aligns with the small step label). */
const NODE_OFFSET = 10
/** How far below a section's top border the line turns toward the next section. */
const TURN_OFFSET = 44
const RADIUS = 24

interface Node {
  x: number
  y: number
  /** Top of the section (its border line), used to route turns through whitespace. */
  sectionTop: number
}

interface Layout {
  width: number
  height: number
  nodes: Node[]
}

/** Offset of `el` relative to `root`, ignoring CSS transforms (reveal/parallax). */
function offsetWithin(el: HTMLElement, root: HTMLElement) {
  let top = 0
  let left = 0
  let node: HTMLElement | null = el
  while (node && node !== root) {
    top += node.offsetTop
    left += node.offsetLeft
    node = node.offsetParent as HTMLElement | null
  }
  return { top, left }
}

/** Vertical line, or a rounded dog-leg that turns in the gap at the top of the next section. */
function segmentPath(a: Node, b: Node) {
  if (Math.abs(a.x - b.x) < 1) return `M ${a.x} ${a.y} V ${b.y}`
  const turnY = b.sectionTop + TURN_OFFSET
  const dir = b.x > a.x ? 1 : -1
  const r = Math.min(RADIUS, Math.abs(b.x - a.x) / 2)
  return [
    `M ${a.x} ${a.y}`,
    `V ${turnY - r}`,
    `Q ${a.x} ${turnY} ${a.x + dir * r} ${turnY}`,
    `H ${b.x - dir * r}`,
    `Q ${b.x} ${turnY} ${b.x} ${turnY + r}`,
    `V ${b.y}`,
  ].join(' ')
}

/**
 * Pipeline connecting the sections. It fills up to the step the user is
 * currently on, driven by workflow completion (never by scrolling).
 * Decorative: the sidebar already exposes the same state to assistive tech.
 */
export function ProgressRail() {
  const { state } = useAssessment()
  const reduced = usePrefersReducedMotion()
  const [layout, setLayout] = useState<Layout | null>(null)

  const completed = selectCompleted(state)
  const firstOpen = sections.findIndex((s) => !completed[s.id])
  const currentIndex = firstOpen === -1 ? sections.length - 1 : firstOpen
  const allDone = firstOpen === -1

  useEffect(() => {
    const main = document.getElementById('main')
    if (!main) return
    const measure = () => {
      const nodes: Node[] = []
      for (const s of sections) {
        const section = document.getElementById(s.id)
        const header = section?.querySelector<HTMLElement>('header')
        if (!section || !header) return
        const h = offsetWithin(header, main)
        nodes.push({
          x: Math.round(h.left - GUTTER),
          y: Math.round(h.top + NODE_OFFSET),
          sectionTop: offsetWithin(section, main).top,
        })
      }
      const next = { width: main.offsetWidth, height: main.offsetHeight, nodes }
      setLayout((prev) => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(main)
    window.addEventListener('resize', measure)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [])

  if (!layout) return null
  const { nodes } = layout
  const draw = reduced ? { duration: 0 } : { duration: 1.1, ease: EASE_FLOW }

  return (
    <div aria-hidden data-print="hide" className="pointer-events-none absolute inset-0 z-0">
      <svg width={layout.width} height={layout.height} className="absolute top-0 left-0 overflow-visible">
        {nodes.slice(1).map((b, i) => {
          const d = segmentPath(nodes[i], b)
          const filled = i + 1 <= currentIndex
          return (
            <g key={sections[i + 1].id} fill="none" strokeWidth={2} strokeLinecap="round">
              <path d={d} stroke="var(--color-line)" />
              <motion.path
                d={d}
                stroke="var(--color-accent)"
                initial={false}
                animate={{ pathLength: filled ? 1 : 0, opacity: filled ? 1 : 0 }}
                transition={draw}
              />
            </g>
          )
        })}
      </svg>

      {nodes.map((n, i) => {
        const done = completed[sections[i].id]
        const current = !allDone && i === currentIndex
        return (
          <div
            key={sections[i].id}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: n.x, top: n.y }}
          >
            {current && !reduced && (
              <span className="absolute inset-0 animate-ping rounded-full bg-accent/25" />
            )}
            <motion.span
              initial={false}
              animate={{ scale: done || current ? 1 : 0.85 }}
              transition={{ type: 'spring', stiffness: 400, damping: 22 }}
              className={`relative flex size-[18px] items-center justify-center rounded-full border-2 transition-colors duration-500 ${
                done
                  ? 'border-accent bg-accent text-white'
                  : current
                    ? 'border-accent bg-white'
                    : 'border-line bg-white'
              }`}
            >
              {done && <Check className="size-2.5" strokeWidth={3.5} />}
            </motion.span>
          </div>
        )
      })}
    </div>
  )
}
