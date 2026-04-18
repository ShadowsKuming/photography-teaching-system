import { useState } from 'react'
import { listProfiles } from '../api/client'

interface Props {
  onNewStudent: () => void
  onReturningStudent: (name: string) => void
}

export function Landing({ onNewStudent, onReturningStudent }: Props) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleContinue = async () => {
    const trimmed = name.trim()
    if (!trimmed) { setError('Please enter your name.'); return }
    setIsLoading(true)
    setError('')
    try {
      const profiles = await listProfiles()
      const match = profiles.find((p) => p.toLowerCase() === trimmed.toLowerCase().replace(/\s+/g, '_'))
      if (!match) {
        setError(`No profile found for "${trimmed}". Start as a new student instead.`)
        return
      }
      onReturningStudent(trimmed)
    } catch {
      setError('Could not connect to the server. Is it running?')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-slate-950 px-6 text-white">
      {/* Logo / branding */}
      <div className="mb-10 text-center">
        <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-3xl shadow-lg">
          📷
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Photography Coach</h1>
        <p className="mt-1 text-sm text-slate-400">Your personal AI photography teacher</p>
      </div>

      {/* Actions */}
      <div className="w-full max-w-sm space-y-4">
        <button
          type="button"
          onClick={onNewStudent}
          className="w-full rounded-2xl bg-indigo-600 px-6 py-4 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 active:scale-95"
        >
          I'm new here — start learning
        </button>

        <div className="relative flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-800" />
          <span className="text-xs text-slate-500">or</span>
          <div className="h-px flex-1 bg-slate-800" />
        </div>

        <div className="space-y-2">
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handleContinue()}
            placeholder="Enter your name to continue…"
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="button"
            disabled={isLoading}
            onClick={handleContinue}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white disabled:opacity-40"
          >
            {isLoading ? 'Checking…' : 'Continue learning'}
          </button>
        </div>
      </div>
    </div>
  )
}
