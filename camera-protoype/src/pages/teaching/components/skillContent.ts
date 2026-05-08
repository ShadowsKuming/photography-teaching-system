import type { TargetSkill } from '../../../types'

export interface SkillLevelInfo {
  /** Short title for this stage (e.g. "Awareness", "Mastery") */
  title: string
  /** What the photographer can newly do at this level — the gain over the previous one. */
  gain: string
}

export interface SkillContent {
  /** One-line description of what this skill is about. */
  blurb: string
  /** Five level descriptions (index 0 = level 1). */
  levels: [SkillLevelInfo, SkillLevelInfo, SkillLevelInfo, SkillLevelInfo, SkillLevelInfo]
}

export const SKILL_CONTENT: Record<TargetSkill, SkillContent> = {
  composition: {
    blurb: 'Where things sit in the frame and how the eye moves through it.',
    levels: [
      { title: 'Awareness',          gain: 'You notice where things sit in the frame and avoid centering everything by default.' },
      { title: 'Rule of thirds',     gain: 'You place subjects off-center on purpose, giving photos stronger structure.' },
      { title: 'Leading the eye',    gain: 'You use lines, shapes, and negative space to guide attention where you want it.' },
      { title: 'Visual rhythm',      gain: 'You balance multiple elements so every part of the frame contributes to the story.' },
      { title: 'Effortless framing', gain: 'You break compositional rules with intent — viewers instantly read what matters.' },
    ],
  },

  lighting: {
    blurb: 'Reading light and using it to shape mood, depth, and dimension.',
    levels: [
      { title: 'Seeing light',       gain: 'You spot when light is too harsh, too flat, or too dim for the shot you want.' },
      { title: 'Finding soft light', gain: 'You position subjects toward windows, shade, or even sources for flattering results.' },
      { title: 'Shaping with shadow', gain: 'You direct light and shadow intentionally to add depth and dimension.' },
      { title: 'Reading mixed light', gain: 'You handle complex lighting and bend it to set the mood you want.' },
      { title: 'Lighting design',     gain: 'You can turn almost any environment into something cinematic.' },
    ],
  },

  subject_clarity: {
    blurb: 'Making sure your subject is unmistakable in every frame.',
    levels: [
      { title: 'In focus',           gain: 'Your subject is sharp, visible, and clearly the point of the photo.' },
      { title: 'Separation',         gain: 'You make the subject stand out from busy backgrounds.' },
      { title: 'Drawing the eye',    gain: 'You direct attention with focus, scale, and contrast.' },
      { title: 'Reads instantly',    gain: 'Your subject is unmistakable, even in complex scenes.' },
      { title: 'Total command',      gain: 'Every element in the frame supports the subject — nothing competes.' },
    ],
  },

  pose_expression: {
    blurb: 'Helping people look natural, confident, and like themselves.',
    levels: [
      { title: 'Comfortable subjects', gain: 'People look relaxed and engaged, not stiff or distracted.' },
      { title: 'Simple direction',     gain: 'You give light cues so poses feel natural rather than posed.' },
      { title: 'Authentic moments',    gain: 'You catch real expressions and small in-between gestures.' },
      { title: 'Storytelling pose',    gain: 'You shape posture, hands, and gaze with intention.' },
      { title: 'Directing presence',   gain: 'You bring out personality in any subject, in any setting.' },
    ],
  },

  background_control: {
    blurb: 'Controlling everything behind the subject so the frame stays clean.',
    levels: [
      { title: 'Spotting clutter',     gain: 'You notice obvious distractions behind your subject before pressing the shutter.' },
      { title: 'Cleaning the frame',   gain: 'You shift angle, distance, or depth to remove visual noise.' },
      { title: 'Complementary backdrops', gain: 'You actively choose backgrounds that support the subject.' },
      { title: 'Tonal balance',        gain: 'You use color, texture, and depth in the background to set mood.' },
      { title: 'Backgrounds that speak', gain: 'The background carries meaning — it adds to the story, not just space.' },
    ],
  },
}

/**
 * A single short sentence describing the photographer's current learning state in this skill.
 * Returns a different message at level 0 (not started) and level 5 (mastered).
 */
export function describeCurrentState(skill: TargetSkill, level: number): string {
  if (level <= 0) {
    return `Not started yet. We'll begin with: ${SKILL_CONTENT[skill].levels[0].gain}`
  }
  if (level >= 5) {
    return `You've mastered this skill — ${SKILL_CONTENT[skill].levels[4].gain.toLowerCase()}`
  }
  return SKILL_CONTENT[skill].levels[level - 1].gain
}

/**
 * Short hint about what the next level will unlock. Empty string if already at max.
 */
export function describeNextStep(skill: TargetSkill, level: number): string {
  if (level >= 5) return ''
  const next = SKILL_CONTENT[skill].levels[Math.max(0, level)]
  return `Up next — ${next.title}: ${next.gain}`
}
