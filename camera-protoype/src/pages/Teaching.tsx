import { useRef, useState } from 'react'
import { Camera } from '../components/Camera'
import { SkillProgress } from '../components/SkillProgress'
import { useTeaching } from '../hooks/useTeaching'
import { buildMinimalLiveCtx } from '../types'
import type { RecommendedAction } from '../types'

interface Props {
  studentName: string
}

type Step = 'lesson' | 'camera' | 'intent' | 'evaluating' | 'feedback'

const ACTION_LABELS: Record<RecommendedAction, string> = {
  retry:        'Try again',
  guided_retry: 'Try again',
  advance:      'Next challenge',
  end_lesson:   'End lesson',
}

export function Teaching({ studentName }: Props) {
  const { profile, lessonPlan, result, isLoading, error, submitPhoto, nextLesson } =
    useTeaching(studentName)

  const [step, setStep] = useState<Step>('lesson')
  const [capturedImage, setCapturedImage] = useState<string | null>(null)   // base64
  const [shotIntent, setShotIntent] = useState('')
  const [showProgress, setShowProgress] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Camera handlers ────────────────────────────────────────────────────────
  const handleCapture = (base64: string) => {
    setCapturedImage(base64)
    setShotIntent('')
    setStep('intent')
  }

  const handleCameraCancel = () => setStep('lesson')

  // ── File upload handler ────────────────────────────────────────────────────
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      // Strip data URL prefix → raw base64
      const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl
      setCapturedImage(base64)
      setShotIntent('')
      setStep('intent')
    }
    reader.readAsDataURL(file)
    // Reset so the same file can be re-selected
    e.target.value = ''
  }

  // ── Submit photo ───────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!capturedImage || !lessonPlan) return
    setStep('evaluating')
    const liveCtx = buildMinimalLiveCtx(lessonPlan.target_skill)
    await submitPhoto(capturedImage, liveCtx, shotIntent || undefined)
    setStep('feedback')
  }

  // ── Action button ──────────────────────────────────────────────────────────
  const handleAction = async () => {
    if (!result) return
    if (result.recommended_action === 'advance' || result.recommended_action === 'end_lesson') {
      await nextLesson()
    }
    setCapturedImage(null)
    setShotIntent('')
    setStep('lesson')
  }

  // ── Loading / error states ─────────────────────────────────────────────────
  if (!profile || !lessonPlan) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-950 text-white">
        {error ? (
          <p className="max-w-xs text-center text-sm text-red-400">{error}</p>
        ) : (
          <p className="text-sm text-slate-400 animate-pulse">Preparing your lesson…</p>
        )}
      </div>
    )
  }

  // ── Camera overlay ─────────────────────────────────────────────────────────
  if (step === 'camera') {
    return (
      <Camera
        targetSkill={lessonPlan.target_skill}
        onCapture={handleCapture}
        onCancel={handleCameraCancel}
      />
    )
  }

  // ── Main UI ────────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-dvh flex-col bg-slate-950 text-white">
      {/* Header */}
      <header
        className="shrink-0 border-b border-slate-800 bg-slate-900/80 px-4 py-3 backdrop-blur-md"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📷</span>
            <div>
              <p className="text-xs font-medium text-indigo-400 capitalize">
                {lessonPlan.target_skill.replace('_', ' ')}
              </p>
              <p className="text-sm font-semibold">{studentName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowProgress((v) => !v)}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 transition hover:border-slate-500 hover:text-white"
          >
            Progress
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5">
        <div className="mx-auto max-w-xl space-y-4">

          {/* Progress panel */}
          {showProgress && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Your progress
              </p>
              <SkillProgress profile={profile} />
            </div>
          )}

          {/* Lesson card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-400">
              Today's focus
            </p>
            <p className="text-sm leading-relaxed text-slate-300">{lessonPlan.concept}</p>
          </div>

          {/* Assignment card */}
          <div className="rounded-2xl border border-indigo-900/50 bg-indigo-950/40 p-4">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-400">
              Your assignment
            </p>
            <p className="text-sm font-medium leading-relaxed text-white">{lessonPlan.assignment}</p>
          </div>

          {/* Captured image preview */}
          {capturedImage && step !== 'lesson' && (
            <div className="overflow-hidden rounded-2xl">
              <img
                src={`data:image/jpeg;base64,${capturedImage}`}
                alt="Captured"
                className="w-full object-cover"
                style={{ maxHeight: '40vh' }}
              />
            </div>
          )}

          {/* Shot intent input */}
          {step === 'intent' && (
            <div className="space-y-3">
              <textarea
                value={shotIntent}
                onChange={(e) => setShotIntent(e.target.value)}
                placeholder="What were you trying to achieve with this shot? (optional)"
                rows={2}
                className="w-full resize-none rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={handleSubmit}
                className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 active:scale-95"
              >
                Submit for feedback
              </button>
            </div>
          )}

          {/* Evaluating spinner */}
          {step === 'evaluating' && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
              <p className="animate-pulse text-sm text-slate-400">Analysing your photo…</p>
            </div>
          )}

          {/* Feedback */}
          {step === 'feedback' && result && (
            <div className="space-y-3">
              <div className="rounded-2xl border border-slate-700 bg-slate-900 p-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Feedback
                </p>
                <p className="text-sm leading-relaxed text-slate-200">{result.feedback_text}</p>
              </div>

              {result.milestone_reached && (
                <div className="rounded-2xl border border-amber-700/50 bg-amber-950/40 p-3 text-center">
                  <p className="text-sm font-semibold text-amber-400">
                    Milestone reached: {result.current_milestone}!
                  </p>
                </div>
              )}

              {error && <p className="text-xs text-red-400">{error}</p>}

              <button
                type="button"
                onClick={handleAction}
                disabled={isLoading}
                className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 active:scale-95"
              >
                {isLoading ? 'Loading…' : ACTION_LABELS[result.recommended_action]}
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Photo input — shown on lesson step */}
      {step === 'lesson' && (
        <div
          className="shrink-0 border-t border-slate-800 bg-slate-900/80 px-4 py-4 backdrop-blur-md"
          style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}
        >
          <div className="mx-auto flex max-w-xl gap-3">
            {/* Take photo */}
            <button
              type="button"
              onClick={() => setStep('camera')}
              className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-4 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 active:scale-95"
            >
              <span className="text-lg" aria-hidden>📷</span>
              Take photo
            </button>

            {/* Upload photo */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-1 items-center justify-center gap-2 rounded-2xl border border-slate-600 bg-slate-800 py-4 text-sm font-semibold text-slate-200 transition hover:border-slate-400 hover:text-white active:scale-95"
            >
              <span className="text-lg" aria-hidden>🖼</span>
              Upload photo
            </button>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* On intent step — allow replacing the photo */}
      {step === 'intent' && (
        <div
          className="shrink-0 border-t border-slate-800 bg-slate-900/80 px-4 py-3 backdrop-blur-md"
          style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
        >
          <div className="mx-auto flex max-w-xl gap-2">
            <button
              type="button"
              onClick={() => { setCapturedImage(null); setStep('camera') }}
              className="flex-1 rounded-xl border border-slate-700 py-2.5 text-xs text-slate-400 transition hover:border-slate-500 hover:text-white"
            >
              Retake
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex-1 rounded-xl border border-slate-700 py-2.5 text-xs text-slate-400 transition hover:border-slate-500 hover:text-white"
            >
              Choose file
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}
    </div>
  )
}
