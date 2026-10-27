// Shared motion tokens so every transition on the page moves with the same feel.

/** Long, soft deceleration ("ease-out-expo"-like). */
export const EASE_FLOW = [0.22, 1, 0.36, 1] as const

/** Section reveal timing. */
export const REVEAL = { duration: 0.8, distance: 24, stagger: 0.12 }

/** Spring applied to scroll progress so parallax trails the scroll slightly instead of locking to it. */
export const SCROLL_SPRING = { stiffness: 90, damping: 24, mass: 0.5, restDelta: 0.0005 }

/** Fade used when content inside a section changes state. */
export const SWAP = { duration: 0.45, distance: 10 }
