import { useNavigation } from '../../state/Navigation'

export function Wordmark() {
  const { goToSection } = useNavigation()
  return (
    <a
      href="#device"
      onClick={(e) => {
        e.preventDefault()
        goToSection('device')
      }}
      className="inline-flex min-h-11 items-center text-[19px] font-semibold tracking-[-0.02em] text-ink"
      aria-label="E-waste Sorter — go to the start"
    >
      E-waste Sorter
    </a>
  )
}
