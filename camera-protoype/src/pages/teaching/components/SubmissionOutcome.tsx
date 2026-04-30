import type { SubmitResult } from '../../../types'

interface SubmissionOutcomeProps {
  result: SubmitResult
}

function isSuccessful(result: SubmitResult): boolean {
  return result.recommended_action === 'advance' || result.recommended_action === 'end_lesson'
}

export function SubmissionOutcome({ result }: SubmissionOutcomeProps) {
  const success = isSuccessful(result)
  const title = success ? 'Successful submission' : 'Not successful yet'
  const subtitle = success
    ? 'Great shot. You completed this challenge and can move forward.'
    : 'This one still needs work. Use the feedback to improve and try again.'

  const iconWrapClass = success
    ? 'border-emerald-600/60 bg-emerald-500/10 text-emerald-300'
    : 'border-amber-600/60 bg-amber-500/10 text-amber-300'

  const titleClass = success ? 'text-emerald-300' : 'text-amber-300'
  const cardClass = success
    ? 'border-emerald-900/60 bg-emerald-950/30'
    : 'border-amber-900/60 bg-amber-950/30'

  return (
    <section className={`rounded-2xl border p-4 ${cardClass}`} aria-live="polite">
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-xl font-semibold ${iconWrapClass}`}
          aria-hidden
        >
          {success ? '✓' : '!'}
        </div>

        <div>
          <p className={`text-sm font-semibold ${titleClass}`}>{title}</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-300">{subtitle}</p>
        </div>
      </div>
    </section>
  )
}
