import { useState } from 'react'
import { Landing } from './pages/Landing'
import { Interview } from './pages/Interview'
import { Teaching } from './pages/Teaching'
import type { Profile } from './types'
import { getCopy, I18nProvider } from './i18n'
import type { AppLocale } from './i18n'

type AppPage = 'landing' | 'interview' | 'teaching'

export function App() {
  const [page, setPage] = useState<AppPage>('landing')
  const [studentName, setStudentName] = useState('')
  const [locale, setLocale] = useState<AppLocale>('en-GB')
  const copy = getCopy(locale)

  const handleInterviewComplete = (profile: Profile) => {
    setStudentName(profile.name)
    setPage('teaching')
  }

  const handleReturningStudent = (name: string) => {
    setStudentName(name)
    setPage('teaching')
  }

  if (page === 'landing') {
    return (
      <I18nProvider locale={locale} setLocale={setLocale} copy={copy}>
        <Landing
          onNewStudent={() => setPage('interview')}
          onReturningStudent={handleReturningStudent}
        />
      </I18nProvider>
    )
  }

  if (page === 'interview') {
    return (
      <I18nProvider locale={locale} setLocale={setLocale} copy={copy}>
        <Interview onComplete={handleInterviewComplete} />
      </I18nProvider>
    )
  }

  return (
    <I18nProvider locale={locale} setLocale={setLocale} copy={copy}>
      <Teaching studentName={studentName} />
    </I18nProvider>
  )
}
