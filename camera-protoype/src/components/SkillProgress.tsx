import type { MilestoneLevel, Profile, TargetSkill } from '../types'

const SKILL_LABELS: Record<TargetSkill, string> = {
  composition:        'Composition',
  lighting:           'Lighting',
  subject_clarity:    'Subject Clarity',
  pose_expression:    'Pose & Expression',
  background_control: 'Background',
}

const MILESTONE_COLORS: Record<MilestoneLevel, string> = {
  beginner:     'bg-slate-400',
  developing:   'bg-sky-500',
  intermediate: 'bg-indigo-500',
  advanced:     'bg-amber-500',
}

interface Props {
  profile: Profile
  compact?: boolean
}

export function SkillProgress({ profile, compact }: Props) {
  const skills = Object.entries(profile.skill_state) as [TargetSkill, { level: number }][]

  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-3'}>
      {/* Milestone badge */}
      <div className="flex items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize text-white ${MILESTONE_COLORS[profile.milestone]}`}
        >
          {profile.milestone}
        </span>
        {!compact && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {profile.name}
          </span>
        )}
      </div>

      {/* Skill bars */}
      {skills.map(([skill, { level }]) => {
        // pose_expression hidden for non-portrait subjects
        if (skill === 'pose_expression' && profile.primary_subject !== 'portrait') return null
        return (
          <div key={skill}>
            <div className="mb-0.5 flex justify-between text-xs">
              <span className="text-slate-600 dark:text-slate-400">{SKILL_LABELS[skill]}</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">{level}/5</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${(level / 5) * 100}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
