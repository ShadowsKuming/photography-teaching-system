import { useState } from 'react'
import { listProfiles } from '../api/client'
import { LanguageSelector } from '../components/LanguageSelector'
import { useI18n } from '../i18n'

interface Props {
  onNewStudent: () => void
  onReturningStudent: (name: string) => void
}

export function Landing({ onNewStudent, onReturningStudent }: Props) {
  const { locale, setLocale, copy } = useI18n()
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleContinue = async () => {
    const trimmed = name.trim()
    if (!trimmed) { setError(copy.enterNameError); return }
    setIsLoading(true)
    setError('')
    try {
      const profiles = await listProfiles()
      const match = profiles.find((p) => p.toLowerCase() === trimmed.toLowerCase().replace(/\s+/g, '_'))
      if (!match) {
        setError(copy.noProfileError(trimmed))
        return
      }
      onReturningStudent(trimmed)
    } catch {
      setError(copy.serverError)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center bg-slate-950 px-6 text-white">
      <div className="absolute right-4 top-4">
        <LanguageSelector locale={locale} onChange={setLocale} />
      </div>

      {/* Logo / branding */}
      <div className="mb-10 text-center">
        <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-3xl shadow-lg">
          📷
        </div>
        <h1 className="text-2xl font-bold tracking-tight">{copy.appName}</h1>
        <p className="mt-1 text-sm text-slate-400">{copy.appTagline}</p>
      </div>

      {/* Actions */}
      <div className="w-full max-w-sm space-y-4">
        <button
          type="button"
          onClick={onNewStudent}
          className="w-full rounded-2xl bg-indigo-600 px-6 py-4 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 active:scale-95"
        >
          {copy.newStudentCta}
        </button>

        <div className="relative flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-800" />
          <span className="text-xs text-slate-500">{copy.separatorOr}</span>
          <div className="h-px flex-1 bg-slate-800" />
        </div>

        <div className="space-y-2">
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handleContinue()}
            placeholder={copy.returningStudentPlaceholder}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="button"
            disabled={isLoading}
            onClick={handleContinue}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white disabled:opacity-40"
          >
            {isLoading ? copy.checkingLabel : copy.continueLearningCta}
          </button>
        </div>
      </div>
    </div>
  )
}
