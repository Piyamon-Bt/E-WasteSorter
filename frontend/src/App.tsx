import { AnalysisStatus } from './components/assessment/AnalysisStatus'
import { DeviceModel, DevicePicker } from './components/assessment/DevicePicker'
import { FunctionalityForm } from './components/assessment/FunctionalityForm'
import { IdentityForm } from './components/assessment/IdentityForm'
import { LocationForm } from './components/assessment/LocationForm'
import { PhotoUploader } from './components/assessment/PhotoUploader'
import { ResultsSummary } from './components/assessment/ResultsSummary'
import { ReviewPanel } from './components/assessment/ReviewPanel'
import { AppSidebar } from './components/layout/AppSidebar'
import { JourneySection } from './components/layout/JourneySection'
import { MobileNavigation } from './components/layout/MobileNavigation'
import { ModeBanner } from './components/layout/ModeBanner'
import { ProgressRail } from './components/layout/ProgressRail'
import { sectionById } from './content/sections'
import { AnnouncerProvider } from './state/Announcer'
import { AssessmentProvider } from './state/AssessmentContext'
import { BackendProvider } from './state/Backend'
import { NavigationProvider } from './state/Navigation'

export default function App() {
  return (
    <AnnouncerProvider>
      <BackendProvider>
        <AssessmentProvider>
          <NavigationProvider>
            <a
              href="#main"
              className="sr-only z-50 rounded-md bg-ink px-4 py-3 text-white focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
            >
              Skip to content
            </a>
            <AppSidebar />
            <MobileNavigation />
            <main
              id="main"
              tabIndex={-1}
              className="relative pt-[var(--header-h)] outline-none lg:ml-[var(--sidebar-w)] lg:pt-0"
            >
              <ModeBanner />
              <JourneySection config={sectionById.device} reveal={false} media={<DeviceModel />} mediaDesktopOnly>
                <DevicePicker />
                <div className="mt-14">
                  <PhotoUploader />
                </div>
              </JourneySection>
              <JourneySection config={sectionById.analyze}>
                <AnalysisStatus />
              </JourneySection>
              <JourneySection config={sectionById.review}>
                <ReviewPanel />
              </JourneySection>
              <JourneySection config={sectionById.functionality}>
                <FunctionalityForm />
              </JourneySection>
              <JourneySection config={sectionById.identity}>
                <IdentityForm />
              </JourneySection>
              <JourneySection config={sectionById.location}>
                <LocationForm />
              </JourneySection>
              <JourneySection config={sectionById.results} printHidden={false}>
                <ResultsSummary />
              </JourneySection>
              <div id="page-end" aria-hidden className="h-px" />
              <ProgressRail />
            </main>
          </NavigationProvider>
        </AssessmentProvider>
      </BackendProvider>
    </AnnouncerProvider>
  )
}
