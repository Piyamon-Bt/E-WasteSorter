// Browser-side assessment types. Assessment data lives only in memory.

export type SectionId = 'device' | 'analyze' | 'review' | 'functionality' | 'identity' | 'location' | 'results'

export type { DeviceType } from './api'

export type AsyncStatus = 'idle' | 'processing' | 'complete' | 'failed'

/** A device photo assigned to a view slot. Never mixed with editorial assets. */
export interface SlotPhoto {
  id: string
  file: File
  /** Temporary object URL — revoked when the photo is removed or replaced. */
  url: string
  /** Required view id (e.g. "front") or "detail" for extra close-ups. */
  slot: string
  width: number
  height: number
}

export interface ReviewDraft {
  response: 'agree' | 'disagree' | 'unsure' | null
  note: string
  extraPhotos: SlotPhoto[]
  followUpStatus: AsyncStatus
  followUpError: string | null
}
