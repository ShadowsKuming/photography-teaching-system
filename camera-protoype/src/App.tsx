import { useEffect, useState } from 'react'
import { Landing } from './pages/Landing'
import { Interview } from './pages/Interview'
import { Teaching } from './pages/Teaching'
import type { Profile } from './types'
import { getCopy, I18nProvider } from './i18n'
import type { AppLocale } from './i18n'

type AppPage = 'landing' | 'interview' | 'teaching'

export function App() {
  const [page, setPage] = useState<AppPage>('landing')
  const [studentId, setStudentId] = useState('')
  const [locale, setLocale] = useState<AppLocale>('pt-BR')
  const copy = getCopy(locale)

  // Resume automatically if a student_id is stored from a previous session
  useEffect(() => {
    const saved = localStorage.getItem('student_id')
    if (saved) {
      setStudentId(saved)
      setPage('teaching')
    }
  }, [])

  const handleInterviewComplete = (profile: Profile) => {
    setStudentId(profile.student_id)
    setPage('teaching')
  }

  const handleReturningStudent = (id: string) => {
    setStudentId(id)
    setPage('teaching')
  }

  const handleBack = () => {
    setStudentId('')
    setPage('landing')
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
        <Interview
          onComplete={handleInterviewComplete}
          onBack={() => setPage('landing')}
        />
      </I18nProvider>
    )
  }

  return (
    <I18nProvider locale={locale} setLocale={setLocale} copy={copy}>
      <Teaching
        studentId={studentId}
        onBack={handleBack}
      />
    </I18nProvider>
  )
}
