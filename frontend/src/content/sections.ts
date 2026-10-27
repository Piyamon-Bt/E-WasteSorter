// Single source of truth for section order, anchors, sidebar labels,
// editorial copy and media placement.

import type { SectionId } from '../types/assessment'
import type { EditorialAssetId } from './assets'

export interface SectionConfig {
  id: SectionId
  number: string
  navLabel: string
  heading: string
  intro: string
  mediaId?: EditorialAssetId
  /** Which side the editorial media sits on at desktop widths. */
  mediaSide: 'left' | 'right'
  /** Give the media half the row and let it extend into the outer margin (for wide scenes). */
  mediaWide?: boolean
}

export const sections: SectionConfig[] = [
  {
    id: 'device',
    number: '01',
    navLabel: 'Device & photos',
    heading: 'Photograph your device',
    intro:
      'One laptop or mobile phone per assessment. Switch the device off and keep it off, then add a photo for every required view. Closing or refreshing this page clears the assessment.',
    mediaSide: 'right',
  },
  {
    id: 'analyze',
    number: '02',
    navLabel: 'Analyze',
    heading: 'Assessing visible condition',
    intro:
      'All views are assessed together as one device. Damage seen in one view stays on record even if other views look normal.',
    mediaId: 'analyze-visual',
    mediaSide: 'left',
    mediaWide: true,
  },
  {
    id: 'review',
    number: '03',
    navLabel: 'Review',
    heading: 'Review the observations',
    intro:
      'Tell us whether each observation matches your device. If you disagree or are unsure, add photos of that area and we will re-check it.',
    mediaSide: 'right',
  },
  {
    id: 'functionality',
    number: '04',
    navLabel: 'Functional checks',
    heading: 'Basic functional checks',
    intro:
      'Simple checks you can do without opening the device. Unknown is never treated as working, and missing answers keep the result conditional.',
    mediaSide: 'left',
  },
  {
    id: 'identity',
    number: '05',
    navLabel: 'Model',
    heading: 'Confirm the model',
    intro:
      'Model-specific prices need the exact model. Confirm, correct or choose Unknown; your choice is recorded separately from what the photos prove.',
    mediaSide: 'right',
  },
  {
    id: 'location',
    number: '06',
    navLabel: 'Location',
    heading: 'Choose your market',
    intro: 'Prices and services are searched in the selected country only. Coverage differs between countries.',
    mediaSide: 'left',
  },
  {
    id: 'results',
    number: '07',
    navLabel: 'Results',
    heading: 'Compare your options',
    intro:
      'Physical findings first, then functional results, local prices and services, and two separate rankings: financial value and resource use.',
    mediaSide: 'right',
  },
]

export const sectionById = Object.fromEntries(sections.map((s) => [s.id, s])) as Record<SectionId, SectionConfig>
