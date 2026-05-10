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

      <div className="relative shrink-0 px-1">
        <ol className="relative z-[1] m-0 grid w-full list-none grid-cols-5 gap-0 p-0">
          {Array.from({ length: STAGE_COUNT }, (_, i) => {
            const stage = i + 1
            const isPast = raw > stage
            const isHere = raw === stage || (raw === 0 && stage === 1)
            const isFuture = raw === 0 ? stage > 1 : raw < stage
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
              />
            )
          })}
        </ol>
      </div>
    </section>
  )
}
