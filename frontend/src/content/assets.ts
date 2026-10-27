// Editorial media configuration.
//
// These are presentation assets for the page (renders, photographs, 3D models).
// They are NOT the user's device photos — those live only in assessment state.
//
// To add an asset: drop the file into /public/assets/images or /public/assets/models
// and set `src` (and optionally `poster`) below. Leave `src` undefined to keep
// an intentional empty slot. No component changes are required.

export type MediaType = 'image' | 'model'

export interface MediaAsset {
  id: string
  type: MediaType
  /** e.g. '/assets/images/upload.webp' or '/assets/models/laptop.glb' */
  src?: string
  /** Optional still shown while a model loads, and as its fallback. */
  poster?: string
  /** Describe the asset for screen readers. Leave empty only for purely decorative media. */
  alt: string
  /** CSS aspect-ratio, e.g. '4 / 5'. Reserves space to avoid layout shift. */
  aspectRatio: string
  objectFit?: 'contain' | 'cover'
  /** Desired parallax travel in px (clamped to 0–48 and reduced on mobile). */
  parallaxStrength?: number
  /**
   * Models only: initial camera, e.g. '-30deg 72deg auto' (theta phi radius).
   * A radius below 100% (e.g. '62%') moves closer than the automatic framing, so the model renders larger.
   */
  cameraOrbit?: string
  /** Models only: slow showcase rotation. Defaults to true. */
  autoRotate?: boolean
}

export const editorialAssets = {
  'upload-visual': {
    id: 'upload-visual',
    type: 'image',
    src: undefined,
    alt: 'Device prepared for photographing',
    aspectRatio: '4 / 5',
    objectFit: 'contain',
    parallaxStrength: 36,
  },
  'analyze-visual': {
    id: 'analyze-visual',
    type: 'model',
    // Placeholder: a desktop computer model, used until a dedicated analysis visual exists.
    src: '/assets/models/retro-computer.glb',
    alt: '3D model of a desktop computer with monitor, keyboard and mouse',
    aspectRatio: '3 / 2',
    objectFit: 'contain',
    parallaxStrength: 40,
    cameraOrbit: '30deg 72deg auto',
  },
  'review-visual': {
    id: 'review-visual',
    type: 'image',
    src: undefined,
    alt: 'Close-up of a device part',
    aspectRatio: '3 / 4',
    objectFit: 'contain',
    parallaxStrength: 28,
  },
  'functionality-visual': {
    id: 'functionality-visual',
    type: 'image',
    src: undefined,
    alt: 'Device powered on',
    aspectRatio: '4 / 5',
    objectFit: 'contain',
    parallaxStrength: 32,
  },
  'results-visual': {
    id: 'results-visual',
    type: 'model',
    src: undefined,
    poster: undefined,
    alt: '3D model of a refurbished device',
    aspectRatio: '1 / 1',
    objectFit: 'contain',
    parallaxStrength: 24,
  },
} satisfies Record<string, MediaAsset>

export type EditorialAssetId = keyof typeof editorialAssets
