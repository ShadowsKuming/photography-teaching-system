import type { SubmitResult } from '../../../types'

interface SubmissionOutcomeProps {
  result: SubmitResult
}

function isSuccessful(result: SubmitResult): boolean {
  return result.recommended_action === 'advance' || result.recommended_action === 'end_lesson'
}

const SCORE_LABELS: Record<keyof SubmitResult['dimension_scores'], string> = {
  composition: 'Composition',
  lighting: 'Lighting',
  subject_clarity: 'Subject clarity',
  pose_expression: 'Pose & expression',
  background_control: 'Background control',
}

const SCORE_ORDER: Array<keyof SubmitResult['dimension_scores']> = [
  'composition',
  'lighting',
  'subject_clarity',
  'pose_expression',
  'background_control',
]

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

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-xl border border-slate-700/70 bg-slate-900/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Overall</p>
          <p className="mt-1 text-sm font-semibold text-white">{result.overall_score}/100</p>
        </div>
        <div className="rounded-xl border border-indigo-700/50 bg-indigo-950/30 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-indigo-300">Focus skill</p>
          <p className="mt-1 text-sm font-semibold text-indigo-100">{result.focus_score}/100</p>
        </div>
        <div className="rounded-xl border border-amber-700/50 bg-amber-950/30 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-amber-400">XP earned</p>
          <p className="mt-1 text-sm font-semibold text-amber-200">+{result.xp_earned ?? 0}</p>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-slate-700/60 bg-slate-900/50 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Category scores</p>
        <ul className="mt-2 space-y-2">
          {SCORE_ORDER.map((skill) => {
            const value = result.dimension_scores[skill]
            return (
              <li key={skill} className="flex items-center justify-between text-xs">
                <span className="text-slate-300">{SCORE_LABELS[skill]}</span>
                <span className="rounded-md bg-slate-800 px-2 py-0.5 font-semibold text-slate-100">
                  {value === null ? 'N/A' : `${value}/100`}
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
