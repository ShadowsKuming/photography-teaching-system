import type {
  LessonPlan,
  LiveContextInput,
  Profile,
  StyleName,
  SubmitResult,
} from '../types'
import type { AppLocale } from '../i18n'

const BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ── Interview ─────────────────────────────────────────────────────────────────

export async function interviewStart(
  language: AppLocale,
): Promise<{ session_id: string; opening_message: string }> {
  return request('/interview/start', {
    method: 'POST',
    body: JSON.stringify({ language }),
  })
}

export async function interviewChat(
  sessionId: string,
  message: string,
  language: AppLocale,
): Promise<{ reply: string; show_style_grid: boolean; is_complete: boolean; state: string }> {
  return request(`/interview/${sessionId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message, language }),
  })
}

export async function interviewStyle(
  sessionId: string,
  selectedStyles: StyleName[],
  language: AppLocale,
): Promise<{ reply: string; state: string }> {
  return request(`/interview/${sessionId}/style`, {
    method: 'POST',
    body: JSON.stringify({ selected_styles: selectedStyles, language }),
  })
}

export async function interviewName(
  sessionId: string,
  name: string,
  language: AppLocale,
): Promise<{ reply: string; is_complete: boolean }> {
  return request(`/interview/${sessionId}/name`, {
    method: 'POST',
    body: JSON.stringify({ name, language }),
  })
}

export async function interviewComplete(
  sessionId: string,
): Promise<{ profile: Profile }> {
  return request(`/interview/${sessionId}/complete`, { method: 'POST' })
}

// ── Teaching ──────────────────────────────────────────────────────────────────

export async function teachStart(
  name: string,
  language: AppLocale,
): Promise<{ session_id: string; lesson_plan: LessonPlan; profile: Profile }> {
  return request('/teach/start', {
    method: 'POST',
    body: JSON.stringify({ name, language }),
  })
}

export async function teachSubmit(
  sessionId: string,
  imageBase64: string,
  liveContext: LiveContextInput,
  shotIntent?: string,
  language?: AppLocale,
): Promise<SubmitResult> {
  return request(`/teach/${sessionId}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      image_base64: imageBase64,
      live_context: liveContext,
      shot_intent: shotIntent ?? null,
      language,
    }),
  })
}

export async function teachNext(
  sessionId: string,
  language?: AppLocale,
): Promise<{ lesson_plan: LessonPlan }> {
  return request(`/teach/${sessionId}/next`, {
    method: 'POST',
    body: JSON.stringify({ language }),
  })
}

export async function getProfile(name: string): Promise<Profile> {
  return request(`/profiles/${encodeURIComponent(name)}`)
}

export async function listProfiles(): Promise<string[]> {
  return request('/profiles')
}
