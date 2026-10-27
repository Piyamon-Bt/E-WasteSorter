import type { SlotPhoto } from '../types/assessment'

export const MAX_BYTES = 10 * 1024 * 1024
export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const ACCEPT_ATTR = '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp'

const EXT = /\.(jpe?g|png|webp)$/i

function formatSize(bytes: number) {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function decode(url: string): Promise<{ width: number; height: number }> {
  const img = new Image()
  img.src = url
  return img.decode().then(() => ({ width: img.naturalWidth, height: img.naturalHeight }))
}

/**
 * Browser-side checks: type, size and decodability. The backend repeats these and
 * also checks resolution and exposure. Rejected files never keep an object URL.
 */
export async function preparePhoto(file: File, slot: string): Promise<{ photo?: SlotPhoto; error?: string }> {
  const typeOk = ACCEPTED_TYPES.includes(file.type) || (!file.type && EXT.test(file.name))
  if (!typeOk) return { error: `“${file.name}” is not a supported format. Use JPG, PNG or WebP.` }
  if (file.size > MAX_BYTES) {
    return { error: `“${file.name}” is ${formatSize(file.size)}. The maximum is 10 MB per photo.` }
  }
  const url = URL.createObjectURL(file)
  try {
    const { width, height } = await decode(url)
    return { photo: { id: crypto.randomUUID(), file, url, slot, width, height } }
  } catch {
    URL.revokeObjectURL(url)
    return { error: `“${file.name}” could not be read as an image. Try another file.` }
  }
}

export async function preparePhotos(files: File[], slot: string, limit: number) {
  const photos: SlotPhoto[] = []
  const errors: string[] = []
  for (const file of files) {
    if (photos.length >= limit) {
      errors.push(`“${file.name}” was not added: the limit is ${limit} extra photos.`)
      continue
    }
    const { photo, error } = await preparePhoto(file, slot)
    if (photo) photos.push(photo)
    if (error) errors.push(error)
  }
  return { photos, errors }
}
