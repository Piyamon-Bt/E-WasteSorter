import { deviceById, devices } from '../../content/devices'
import { useIsDesktop } from '../../hooks/useMediaQuery'
import { useAssessment } from '../../state/AssessmentContext'
import { EmptyMedia } from '../media/EmptyMedia'
import { MediaSlot } from '../media/MediaSlot'
import { ChoiceGroup } from '../ui/ChoiceGroup'

const options = devices.map((d) => ({ value: d.id, label: d.label }))

/** Decorative 3D model of the selected device type (or a quiet empty state). */
export function DeviceModel({ emptyLabel = 'Choose a device type.' }: { emptyLabel?: string }) {
  const { state } = useAssessment()
  const device = state.deviceType ? deviceById[state.deviceType] : null
  if (!device) return <EmptyMedia aspectRatio="1 / 1" label={emptyLabel} />
  return <MediaSlot asset={device.model} />
}

export function DevicePicker() {
  const { state, actions } = useAssessment()
  const isDesktop = useIsDesktop()

  return (
    <div className="space-y-6">
      <ChoiceGroup
        legend="Which device are you assessing?"
        hint="One device per assessment. Changing the type clears the photos."
        name="device-type"
        value={state.deviceType}
        options={options}
        onChange={actions.setDevice}
      />
      {!isDesktop && state.deviceType && (
        <div className="mx-auto max-w-xs sm:max-w-sm">
          <DeviceModel />
        </div>
      )}
    </div>
  )
}
