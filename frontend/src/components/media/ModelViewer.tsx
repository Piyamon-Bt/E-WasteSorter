import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { EmptyMedia } from './EmptyMedia'

interface ModelViewerProps {
  src: string
  poster?: string
  alt: string
  aspectRatio: string
  cameraOrbit?: string
  autoRotate?: boolean
}

let viewerModule: Promise<unknown> | null = null
const loadViewer = () => (viewerModule ??= import('@google/model-viewer'))

function hasWebGL() {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

/**
 * Lazy <model-viewer> wrapper for user-supplied GLB/glTF files.
 * - Library and model load only near the viewport.
 * - Display only: the model turns slowly on its own and ignores pointer input,
 *   so page scrolling is never captured. Rotation stops under reduced motion.
 * - model-viewer pauses rendering itself when off-screen.
 */
export function ModelViewer({
  src,
  poster,
  alt,
  aspectRatio,
  cameraOrbit,
  autoRotate = true,
}: ModelViewerProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<HTMLElement>(null)
  const [near, setNear] = useState(false)
  const [ready, setReady] = useState(false)
  // Tracks which src failed, so switching to another model clears the error.
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  const failed = failedSrc === src
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null)
  const loaded = loadedSrc === src
  const reduced = usePrefersReducedMotion()
  const [webgl] = useState(hasWebGL)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setNear(true)
          io.disconnect()
        }
      },
      { rootMargin: '400px 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    if (!near || !webgl) return
    let active = true
    loadViewer()
      .then(() => active && setReady(true))
      .catch(() => active && setFailedSrc(src))
    return () => {
      active = false
    }
  }, [near, webgl, src])

  useEffect(() => {
    const el = viewerRef.current
    if (!el) return
    const onError = () => setFailedSrc(src)
    const onLoad = () => setLoadedSrc(src)
    el.addEventListener('error', onError)
    el.addEventListener('load', onLoad)
    return () => {
      el.removeEventListener('error', onError)
      el.removeEventListener('load', onLoad)
    }
  }, [ready, src])

  if (failed || !webgl) {
    return poster ? (
      <img src={poster} alt={alt} style={{ aspectRatio }} className="w-full object-contain" />
    ) : (
      <EmptyMedia aspectRatio={aspectRatio} label="3D preview unavailable." />
    )
  }

  return (
    <div ref={wrapRef} className="relative w-full" style={{ aspectRatio }}>
      {ready ? (
        <model-viewer
          ref={viewerRef}
          src={src}
          poster={poster}
          alt={alt}
          loading="lazy"
          interaction-prompt="none"
          auto-rotate={autoRotate && !reduced ? '' : undefined}
          auto-rotate-delay="0"
          rotation-per-second="18deg"
          camera-orbit={cameraOrbit}
          // Allow camera radii below the auto framing so a config can zoom in.
          min-camera-orbit="auto auto 0m"
          environment-image="neutral"
          shadow-intensity="0.6"
          shadow-softness="1"
          style={{
            width: '100%',
            height: '100%',
            background: 'transparent',
            pointerEvents: 'none',
            // Crossfade: fade out while the next model loads, ease back in once it has.
            opacity: loaded ? 1 : 0,
            transform: loaded ? 'scale(1)' : 'scale(0.97)',
            transition:
              'opacity 600ms cubic-bezier(0.22, 1, 0.36, 1), transform 900ms cubic-bezier(0.22, 1, 0.36, 1)',
          }}
        >
          {/* Replaces the built-in progress bar (a dark line at the top) with nothing. */}
          <div slot="progress-bar" />
        </model-viewer>
      ) : poster ? (
        <img src={poster} alt="" className="h-full w-full object-contain" />
      ) : (
        <EmptyMedia aspectRatio={aspectRatio} label="Loading 3D preview…" />
      )}
      {ready && !loaded && (
        <p
          role="status"
          className="pointer-events-none absolute inset-x-0 bottom-4 animate-pulse text-center text-[12px] text-neutral-400 motion-reduce:animate-none"
        >
          Loading 3D model…
        </p>
      )}
    </div>
  )
}
