import type { DetailedHTMLProps, HTMLAttributes } from 'react'

type ModelViewerAttributes = DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement> & {
  src?: string
  poster?: string
  alt?: string
  loading?: 'auto' | 'lazy' | 'eager'
  reveal?: 'auto' | 'manual'
  'camera-controls'?: boolean | ''
  'touch-action'?: 'pan-y' | 'pan-x' | 'none'
  'interaction-prompt'?: 'auto' | 'none'
  'disable-pan'?: boolean | ''
  'shadow-intensity'?: string
  'shadow-softness'?: string
  'camera-orbit'?: string
  'min-camera-orbit'?: string
  'environment-image'?: string
  exposure?: string
  'auto-rotate'?: boolean | ''
  'auto-rotate-delay'?: string
  'rotation-per-second'?: string
}

declare module 'react' {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': ModelViewerAttributes
    }
  }
}
