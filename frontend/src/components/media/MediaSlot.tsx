import { useState } from 'react'
import type { MediaAsset } from '../../content/assets'
import { EmptyMedia } from './EmptyMedia'
import { ModelViewer } from './ModelViewer'

/**
 * Renders a configured editorial asset (image or 3D model).
 * With no `src`, or if loading fails, it keeps the reserved space with a quiet empty state.
 */
export function MediaSlot({ asset }: { asset: MediaAsset }) {
  const [imageFailed, setImageFailed] = useState(false)
  const { src, type, aspectRatio, objectFit = 'contain', alt, poster } = asset

  if (!src) return <EmptyMedia aspectRatio={aspectRatio} />

  if (type === 'model') {
    return (
      <ModelViewer
        src={src}
        poster={poster}
        alt={alt}
        aspectRatio={aspectRatio}
        cameraOrbit={asset.cameraOrbit}
        autoRotate={asset.autoRotate ?? true}
      />
    )
  }

  if (imageFailed) return <EmptyMedia aspectRatio={aspectRatio} label="Image could not be loaded." />

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={() => setImageFailed(true)}
      style={{ aspectRatio, objectFit }}
      className="block w-full"
    />
  )
}
