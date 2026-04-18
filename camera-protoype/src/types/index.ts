// ── Profile ───────────────────────────────────────────────────────────────────

export type PrimaryGoal = 'social_media' | 'portfolio' | 'skill_building'
export type PrimarySubject = 'portrait' | 'scene' | 'object'
export type MilestoneLevel = 'beginner' | 'developing' | 'intermediate' | 'advanced'
export type TargetSkill =
  | 'composition'
  | 'lighting'
  | 'subject_clarity'
  | 'pose_expression'
  | 'background_control'

export type StyleName =
  | 'Warm & Film'
  | 'Clean & Bright'
  | 'Moody & Dark'
  | 'Documentary'
  | 'Soft & Dreamy'
  | 'Gritty & Urban'

export interface SkillLevel {
  level: number
  recent_attempts: string[]
}

export interface Profile {
  name: string
  primary_goal: PrimaryGoal
  primary_subject: PrimarySubject
  style: StyleName
  milestone: MilestoneLevel
  skill_state: Record<TargetSkill, SkillLevel>
  device_type: 'phone' | 'camera'
  device_constraints: string[]
  is_diagnostic: boolean
}

// ── Interview ─────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export type InterviewState = 'chatting' | 'style_shown' | 'naming' | 'complete'

// ── Teaching ──────────────────────────────────────────────────────────────────

export interface LessonPlan {
  target_skill: TargetSkill
  concept: string
  assignment: string
  rationale: string
  is_fallback: boolean
}

export type RecommendedAction = 'retry' | 'guided_retry' | 'advance' | 'end_lesson'

export interface SubmitResult {
  feedback_text: string
  recommended_action: RecommendedAction
  reason: string
  skill_updated: boolean
  milestone_reached: boolean
  current_milestone: MilestoneLevel
  updated_skill_levels: Record<TargetSkill, number>
}

// ── Live context (v1 minimal) ─────────────────────────────────────────────────

export interface LiveContextInput {
  target_skill: TargetSkill
  observed_issues: never[]
  events: never[]
  final_capture_state: {
    composition_status: string
    lighting_status: string
    subject_clarity_status: string
    pose_expression_status: string
    background_control_status: string
  }
  captures: { timestamp: string }[]
}

export function buildMinimalLiveCtx(skill: TargetSkill): LiveContextInput {
  return {
    target_skill: skill,
    observed_issues: [],
    events: [],
    final_capture_state: {
      composition_status: 'acceptable',
      lighting_status: 'acceptable',
      subject_clarity_status: 'acceptable',
      pose_expression_status: 'not_applicable',
      background_control_status: 'acceptable',
    },
    captures: [{ timestamp: new Date().toISOString() }],
  }
}
