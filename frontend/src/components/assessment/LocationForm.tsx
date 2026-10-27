import { LocateFixed } from 'lucide-react'
import { useState } from 'react'
import { countries } from '../../content/labels'
import { useAssessment } from '../../state/AssessmentContext'
import { useNavigation } from '../../state/Navigation'
import { Button } from '../ui/Button'
import { Notice } from '../ui/Notice'

const OTHER = 'other'

/** Country and area selection. Coordinates stay in memory and are only used for this search. */
export function LocationForm() {
  const { state, actions } = useAssessment()
  const { goToSection } = useNavigation()
  const [country, setCountry] = useState(state.location?.country ?? 'TH')
  const [otherCode, setOtherCode] = useState('')
  const [area, setArea] = useState(state.location?.area ?? '')
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(
    state.location?.latitude != null && state.location.longitude != null
      ? { latitude: state.location.latitude, longitude: state.location.longitude }
      : null,
  )
  const [locating, setLocating] = useState(false)
  const [geoError, setGeoError] = useState<string | null>(null)

  if (!state.identity) {
    return (
      <div className="space-y-5">
        <Notice>Choose your market after confirming the model (or choosing Unknown).</Notice>
        <Button variant="secondary" onClick={() => goToSection('identity')}>
          Go to Model
        </Button>
      </div>
    )
  }

  const code = (country === OTHER ? otherCode : country).trim().toUpperCase()
  const validCode = /^[A-Z]{2}$/.test(code)

  function useCurrentLocation() {
    setGeoError(null)
    if (!('geolocation' in navigator)) {
      setGeoError('Location is not available in this browser. Enter your area manually.')
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        setCoords({ latitude: pos.coords.latitude, longitude: pos.coords.longitude })
      },
      () => {
        setLocating(false)
        setCoords(null)
        setGeoError('Location access failed or was declined. Enter your area manually.')
      },
      { timeout: 10000, maximumAge: 60000 },
    )
  }

  function search() {
    actions.setLocation({ country: code, area: area.trim(), latitude: coords?.latitude ?? null, longitude: coords?.longitude ?? null })
    actions.startResearch()
    goToSection('results')
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-[14px] text-muted">
          Country
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-line bg-white px-3 text-[15px] text-ink"
          >
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
            <option value={OTHER}>Other (enter code)</option>
          </select>
        </label>
        {country === OTHER && (
          <label className="block text-[14px] text-muted">
            Two-letter country code (ISO)
            <input
              value={otherCode}
              maxLength={2}
              onChange={(e) => setOtherCode(e.target.value)}
              className="mt-1 min-h-11 w-full rounded-md border border-line px-3 text-[15px] text-ink uppercase"
            />
          </label>
        )}
        <label className="block text-[14px] text-muted sm:col-span-2">
          Area, city or district
          <input
            value={area}
            maxLength={100}
            placeholder="e.g. Bangkok, Chatuchak"
            onChange={(e) => setArea(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-line px-3 text-[15px] text-ink"
          />
        </label>
      </div>

      <div className="space-y-2">
        <Button variant="secondary" onClick={useCurrentLocation} disabled={locating}>
          <LocateFixed aria-hidden className="size-4" /> {locating ? 'Locating…' : 'Use current location'}
        </Button>
        {coords && (
          <p className="text-[14px] text-muted">
            Current location will be used to bias the service search and calculate straight-line distances.{' '}
            <button type="button" className="underline" onClick={() => setCoords(null)}>
              Don’t use it
            </button>
          </p>
        )}
        {geoError && (
          <p role="alert" className="text-[14px] text-danger">
            {geoError}
          </p>
        )}
        <p className="text-[14px] text-muted">
          Your location is not saved. The country you choose limits the price search; current location does not
          change the country.
        </p>
      </div>

      <div className="space-y-2">
        <Button onClick={search} disabled={!validCode || (!area.trim() && !coords) || state.research.status === 'processing'}>
          Search prices and services
        </Button>
        {!area.trim() && !coords && <p className="text-[14px] text-muted">Enter an area or use your current location.</p>}
        {country === OTHER && !validCode && <p className="text-[14px] text-muted">Enter a two-letter country code.</p>}
      </div>
    </div>
  )
}
