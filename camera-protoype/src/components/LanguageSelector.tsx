import type { AppLocale } from '../i18n'
import { localeName } from '../i18n'

interface Props {
  locale: AppLocale
  onChange: (locale: AppLocale) => void
  className?: string
}

export function LanguageSelector({ locale, onChange, className }: Props) {
  return (
    <label
      className={`inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 ${className ?? ''}`}
    >
      <GlobeIcon />
      <select
        value={locale}
        onChange={(e) => onChange(e.target.value as AppLocale)}
        className="bg-transparent pr-1 text-xs outline-none"
        aria-label="Language"
      >
        <option value="en-GB" className="bg-slate-900">English (UK)</option>
        <option value="pt-BR" className="bg-slate-900">Portugues (BR)</option>
      </select>
      <span className="sr-only">{localeName(locale)}</span>
    </label>
  )
}

function GlobeIcon() {
  return (
    <svg
      aria-hidden
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-slate-400"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14.5 14.5 0 0 1 0 18" />
      <path d="M12 3a14.5 14.5 0 0 0 0 18" />
    </svg>
  )
}
