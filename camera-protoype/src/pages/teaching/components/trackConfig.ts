import type { TargetSkill } from '../../../types'

export const STAGE_COUNT = 5

export const STAGE_SHORT: readonly string[] = [
  'Intro',
  'Build',
  'Refine',
  'Stretch',
  'Master',
]

export const SKILL_LABELS: Record<TargetSkill, string> = {
  composition:        'Composition',
  lighting:           'Lighting',
  subject_clarity:    'Subject Clarity',
  pose_expression:    'Pose & Expression',
  background_control: 'Background',
}
