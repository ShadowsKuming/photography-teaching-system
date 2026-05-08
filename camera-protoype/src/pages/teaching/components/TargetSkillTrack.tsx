import type { PrimarySubject, TargetSkill } from '../../../types'
import { TrackStageNode } from './TrackStageNode'
import { SKILL_LABELS, STAGE_COUNT, STAGE_SHORT } from './trackConfig'

interface TargetSkillTrackProps {
  targetSkill: TargetSkill
  currentLevel: number
  primarySubject: PrimarySubject
}

export function TargetSkillTrack({ targetSkill, currentLevel, primarySubject }: TargetSkillTrackProps) {
  if (targetSkill === 'pose_expression' && primarySubject !== 'portrait') {
    return null
  }

  const raw = Math.max(0, Math.min(STAGE_COUNT, Math.round(Number(currentLevel) || 0)))
  const progressPct = raw < 1 ? 0 : (raw / STAGE_COUNT) * 100
  const skillName = SKILL_LABELS[targetSkill]

  return (
    <section
      className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/80 to-slate-950/90 p-4"
      aria-label={`${skillName} skill path, level ${raw} of ${STAGE_COUNT}`}
    >
      <div className="mb-4 flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-bold tracking-tight text-slate-100">{skillName}</h2>
        <span className="text-xs font-medium tabular-nums text-slate-500">
          {raw}/{STAGE_COUNT}
        </span>
      </div>

      <div className="relative min-h-[120px] px-1">
        <svg
          className="pointer-events-none absolute inset-x-0 top-7 h-[72px] w-full"
          viewBox="0 0 400 72"
          preserveAspectRatio="none"
          aria-hidden
        >
          <defs>
            <linearGradient id="teachingTrackGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgb(16 185 129 / 0.95)" />
              <stop offset="100%" stopColor="rgb(99 102 241 / 0.85)" />
            </linearGradient>
          </defs>
          <path
            d="M 16 12 L 384 12"
            fill="none"
            stroke="rgb(51 65 85 / 0.6)"
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            d="M 16 12 L 384 12"
            fill="none"
            pathLength={100}
            stroke="url(#teachingTrackGrad)"
            strokeWidth="4"
            strokeLinecap="round"
            style={{
              strokeDasharray: `${progressPct} 100`,
            }}
          />
        </svg>

        <ol className="relative z-[1] m-0 grid w-full list-none grid-cols-5 gap-0 p-0">
          {Array.from({ length: STAGE_COUNT }, (_, i) => {
            const stage = i + 1
            const isPast = raw > stage
            const isHere = raw === stage || (raw === 0 && stage === 1)
            const isFuture = raw === 0 ? stage > 1 : raw < stage
            const bobY = i % 2 === 0 ? 0 : 7
            const isMaxed = isHere && raw === STAGE_COUNT

            return (
              <TrackStageNode
                key={stage}
                stage={stage}
                label={STAGE_SHORT[i]}
                isPast={isPast}
                isHere={isHere}
                isFuture={isFuture}
                isMaxed={isMaxed}
                bobY={bobY}
              />
            )
          })}
        </ol>
      </div>
    </section>
  )
}
