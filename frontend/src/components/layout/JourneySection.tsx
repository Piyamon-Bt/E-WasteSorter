import { motion, type Variants } from 'motion/react'
import type { ReactNode } from 'react'
import { editorialAssets } from '../../content/assets'
import type { SectionConfig } from '../../content/sections'
import { usePrefersReducedMotion } from '../../hooks/useMediaQuery'
import { EASE_FLOW, REVEAL } from '../../lib/motion'
import { MediaSlot } from '../media/MediaSlot'
import { ParallaxMedia } from '../media/ParallaxMedia'
import { SectionHeading } from './SectionHeading'

interface JourneySectionProps {
  config: SectionConfig
  children: ReactNode
  /** Hide this section's interactive content when printing. */
  printHidden?: boolean
  /** Fade in on first view. Off for the opening section so it is usable immediately. */
  reveal?: boolean
  /** Replaces the configured editorial asset (e.g. the selected device's 3D model). Not parallaxed. */
  media?: ReactNode
  /** Only show the media column at desktop widths (the section renders it inline otherwise). */
  mediaDesktopOnly?: boolean
}

/**
 * One stage of the vertical journey. Desktop: two columns with the editorial
 * media alternating sides. Mobile/tablet: controls first, media after.
 */
const container: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: REVEAL.stagger } },
}
const item: Variants = {
  hidden: { opacity: 0, y: REVEAL.distance },
  shown: { opacity: 1, y: 0, transition: { duration: REVEAL.duration, ease: EASE_FLOW } },
}

export function JourneySection({
  config,
  children,
  printHidden = true,
  reveal = true,
  media,
  mediaDesktopOnly = false,
}: JourneySectionProps) {
  const reduced = usePrefersReducedMotion()
  const asset = config.mediaId ? editorialAssets[config.mediaId] : undefined
  const mediaLeft = config.mediaSide === 'left'

  return (
    <section
      id={config.id}
      data-journey
      aria-labelledby={`${config.id}-heading`}
      data-print={printHidden ? 'hide' : undefined}
      className="relative z-[1] py-16 pr-4 pl-12 first:pt-16 sm:pr-8 sm:pl-16 md:py-28 md:first:pt-32 lg:pr-14 lg:pl-14 xl:pr-20 xl:pl-20"
    >
      <div className="mx-auto grid max-w-[1120px] grid-cols-1 gap-x-16 gap-y-12 lg:grid-cols-12">
        <motion.div
          data-print="static"
          className={`min-w-0 ${config.mediaWide ? 'lg:col-span-6' : 'lg:col-span-7'} ${mediaLeft ? 'lg:order-2' : ''}`}
          variants={container}
          initial={reduced || !reveal ? false : 'hidden'}
          whileInView="shown"
          viewport={{ once: true, margin: '0px 0px -12% 0px' }}
        >
          {/* Heading first, then the section's controls, in a short cascade. */}
          <motion.div variants={item} data-print="static">
            <SectionHeading
              id={config.id}
              number={config.number}
              heading={config.heading}
              intro={config.intro}
            />
          </motion.div>
          <motion.div variants={item} data-print="static">
            {children}
          </motion.div>
        </motion.div>

        {(media || asset) && (
          <motion.div
            data-print="hide"
            className={`min-w-0 lg:pt-16 ${mediaLeft ? 'lg:order-1' : ''} ${
              config.mediaWide ? (mediaLeft ? 'lg:col-span-6 lg:-ml-10' : 'lg:col-span-6 lg:-mr-10') : 'lg:col-span-5'
            } ${
              mediaDesktopOnly ? 'hidden lg:block' : ''
            }`}
            initial={reduced || !reveal ? false : { opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '0px 0px -12% 0px' }}
            transition={{ duration: 1.1, delay: 0.2, ease: EASE_FLOW }}
          >
            <div className="mx-auto max-w-xs md:max-w-md lg:max-w-none">
              {media ? (
                // Custom media (the device model) stays fixed in the layout: no sticky, no parallax.
                media
              ) : (
                asset && (
                  <ParallaxMedia strength={asset.parallaxStrength}>
                    <MediaSlot asset={asset} />
                  </ParallaxMedia>
                )
              )}
            </div>
          </motion.div>
        )}
      </div>
    </section>
  )
}
