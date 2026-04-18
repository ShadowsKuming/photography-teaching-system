import { useState } from 'react'
import { Landing } from './pages/Landing'
import { Interview } from './pages/Interview'
import { Teaching } from './pages/Teaching'
import type { Profile } from './types'

type AppPage = 'landing' | 'interview' | 'teaching'

export function App() {
  const [page, setPage] = useState<AppPage>('landing')
  const [studentName, setStudentName] = useState('')

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
      <Landing
        onNewStudent={() => setPage('interview')}
        onReturningStudent={handleReturningStudent}
      />
    )
  }

  if (page === 'interview') {
    return <Interview onComplete={handleInterviewComplete} />
  }

  return <Teaching studentName={studentName} />
}
