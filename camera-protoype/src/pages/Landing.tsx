import { useEffect, useState } from 'react'
import * as api from '../api/client'
import { LanguageSelector } from '../components/LanguageSelector'
import { useI18n } from '../i18n'

interface Props {
  onNewStudent: () => void
  onReturningStudent: (studentId: string) => void
}

type ProfileSummary = { student_id: string; name: string }

function discriminator(studentId: string): string {
  const idx = studentId.lastIndexOf('#')
  return idx >= 0 ? studentId.slice(idx) : ''
}

export function Landing({ onNewStudent, onReturningStudent }: Props) {
  const { locale, setLocale, copy } = useI18n()
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [savedName, setSavedName] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [pickerMatches, setPickerMatches] = useState<ProfileSummary[]>([])

  useEffect(() => {
    const id = localStorage.getItem('student_id')
    const n = localStorage.getItem('student_name')
    if (id && n) { setSavedId(id); setSavedName(n) }
  }, [])

  const handleContinueSaved = () => {
    if (savedId) onReturningStudent(savedId)
  }

  const handleSwitchAccount = () => {
    localStorage.removeItem('student_id')
    localStorage.removeItem('student_name')
    setSavedId(null)
    setSavedName(null)
  }

  const handleSearch = async () => {
    const trimmed = name.trim()
    if (!trimmed) { setError('Please enter your name'); return }
    setIsLoading(true)
    setError('')
    try {
      const all = await api.listProfiles()
      const matches = all.filter(
        (p) => p.name.toLowerCase() === trimmed.toLowerCase()
      )
      if (matches.length === 0) {
        setError(`No account found for "${trimmed}". Are you new here?`)
      } else if (matches.length === 1) {
        choose(matches[0])
      } else {
        setPickerMatches(matches)
      }
    } catch {
      setError(copy.serverError)
    } finally {
      setIsLoading(false)
    }
  }

  const choose = (profile: ProfileSummary) => {
    localStorage.setItem('student_id', profile.student_id)
    localStorage.setItem('student_name', profile.name)
    setPickerMatches([])
    onReturningStudent(profile.student_id)
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center bg-slate-950 px-6 text-white">
      <div className="absolute right-4 top-4">
        <LanguageSelector locale={locale} onChange={setLocale} />
      </div>

      {/* Logo */}
      <div className="mb-10 text-center">
        <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-3xl shadow-lg">
          📷
        </div>
        <h1 className="text-2xl font-bold tracking-tight">{copy.appName}</h1>
        <p className="mt-1 text-sm text-slate-400">{copy.appTagline}</p>
      </div>

      <div className="w-full max-w-sm space-y-4">
        {savedName && savedId ? (
          <>
            <button
              type="button"
              onClick={handleContinueSaved}
              className="w-full rounded-2xl bg-indigo-600 px-6 py-4 text-left shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 active:scale-95"
            >
              <p className="text-xs font-medium text-indigo-200">Continue as</p>
              <p className="mt-0.5 text-base font-bold text-white">{savedName}</p>
              <p className="mt-0.5 text-[10px] text-indigo-300/70">{savedId}</p>
            </button>
            <button
              type="button"
              onClick={handleSwitchAccount}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
            >
              Use a different account
            </button>
          </>
        ) : (
          <>
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
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={copy.returningStudentPlaceholder}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
              {error && (
                <p className="text-xs text-red-400">
                  {error}
                  {error.includes('new here') && (
                    <button
                      type="button"
                      onClick={onNewStudent}
                      className="ml-2 underline"
                    >
                      Start learning
                    </button>
                  )}
                </p>
              )}
              <button
                type="button"
                disabled={isLoading}
                onClick={handleSearch}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white disabled:opacity-40"
              >
                {isLoading ? copy.checkingLabel : copy.continueLearningCta}
              </button>
            </div>
          </>
        )}
      </div>

      {/* ── Picker dialog ─────────────────────────────────────────────────── */}
      {pickerMatches.length > 1 && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center"
          onClick={() => setPickerMatches([])}
        >
          <div
            className="w-full max-w-sm rounded-t-3xl border border-slate-700 bg-slate-900 p-5 sm:rounded-3xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="mb-1 text-sm font-semibold text-white">Which account is yours?</p>
            <p className="mb-4 text-xs text-slate-400">
              Multiple accounts share that name. Pick the one with your ID number.
            </p>
            <ul className="space-y-2">
              {pickerMatches.map((p) => (
                <li key={p.student_id}>
                  <button
                    type="button"
                    onClick={() => choose(p)}
                    className="flex w-full items-center justify-between rounded-2xl border border-slate-700 bg-slate-800 px-4 py-3 text-left transition hover:border-indigo-500 hover:bg-slate-700 active:scale-95"
                  >
                    <span className="text-sm font-medium text-white">{p.name}</span>
                    <span className="rounded-full bg-slate-700 px-2.5 py-0.5 text-xs font-mono font-semibold text-indigo-300">
                      {discriminator(p.student_id)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => setPickerMatches([])}
              className="mt-3 w-full rounded-xl py-2 text-xs text-slate-500 transition hover:text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
