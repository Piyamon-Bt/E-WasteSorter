// Supported device types, their required photo views and decorative 3D models.
// The view ids must match REQUIRED_VIEWS in backend/app/schemas/physical.py.

import type { DeviceType } from '../types/api'
import type { MediaAsset } from './assets'

export interface ViewSlot {
  id: string
  label: string
  hint: string
}

export interface DeviceConfig {
  id: DeviceType
  label: string
  model: MediaAsset
  views: ViewSlot[]
}

const model = (id: DeviceType, file: string, alt: string, cameraOrbit = '30deg 72deg auto'): MediaAsset => ({
  id: `device-${id}`,
  type: 'model',
  src: `/assets/models/${file}`,
  alt,
  aspectRatio: '1 / 1',
  objectFit: 'contain',
  parallaxStrength: 32,
  cameraOrbit,
})

export const DETAIL_SLOT = 'detail'

export const devices: DeviceConfig[] = [
  {
    id: 'laptop',
    label: 'Laptop',
    model: model('laptop', 'retro-laptop.glb', '3D model of a laptop'),
    views: [
      { id: 'screen', label: 'Screen (lid open, powered off)', hint: 'Straight on, whole screen visible.' },
      { id: 'keyboard', label: 'Keyboard and touchpad', hint: 'From above, whole keyboard in frame.' },
      { id: 'lid', label: 'Outer lid', hint: 'Lid closed, from above.' },
      { id: 'underside', label: 'Underside', hint: 'Include any labels or stickers.' },
      { id: 'left', label: 'Left edge / ports', hint: 'A view without ports is still valid.' },
      { id: 'right', label: 'Right edge / ports', hint: 'A view without ports is still valid.' },
    ],
  },
  {
    id: 'mobile',
    label: 'Mobile phone',
    model: model('mobile', 'retro-smartphone.glb', '3D model of a smartphone', '25deg 80deg auto'),
    views: [
      { id: 'front', label: 'Front screen', hint: 'Screen off, straight on, avoid reflections.' },
      { id: 'back', label: 'Back', hint: 'Remove any case.' },
      { id: 'left', label: 'Left edge', hint: 'Edge-on, so gaps or bulges are visible.' },
      { id: 'right', label: 'Right edge', hint: 'Edge-on, so gaps or bulges are visible.' },
      { id: 'top', label: 'Top edge', hint: 'A view without ports is still valid.' },
      { id: 'bottom', label: 'Bottom edge', hint: 'Include the charging port.' },
    ],
  },
]

export const deviceById = Object.fromEntries(devices.map((d) => [d.id, d])) as Record<DeviceType, DeviceConfig>

export function viewLabel(device: DeviceType | null, slot: string): string {
  if (slot === DETAIL_SLOT) return 'Additional detail'
  return (device && deviceById[device].views.find((v) => v.id === slot)?.label) || slot
}
