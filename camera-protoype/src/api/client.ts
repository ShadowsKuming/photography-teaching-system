import type {
  LessonPlan,
  LiveContextInput,
  Profile,
  StyleName,
  SubmitResult,
} from '../types'

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

export async function interviewStart(): Promise<{ session_id: string; opening_message: string }> {
  return request('/interview/start', { method: 'POST' })
}

export async function interviewChat(
  sessionId: string,
  message: string,
): Promise<{ reply: string; show_style_grid: boolean; is_complete: boolean; state: string }> {
  return request(`/interview/${sessionId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function interviewStyle(
  sessionId: string,
  selectedStyles: StyleName[],
): Promise<{ reply: string; state: string }> {
  return request(`/interview/${sessionId}/style`, {
    method: 'POST',
    body: JSON.stringify({ selected_styles: selectedStyles }),
  })
}

export async function interviewName(
  sessionId: string,
  name: string,
): Promise<{ reply: string; is_complete: boolean }> {
  return request(`/interview/${sessionId}/name`, {
    method: 'POST',
    body: JSON.stringify({ name }),
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
): Promise<{ session_id: string; lesson_plan: LessonPlan; profile: Profile }> {
  return request('/teach/start', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export async function teachSubmit(
  sessionId: string,
  imageBase64: string,
  liveContext: LiveContextInput,
  shotIntent?: string,
): Promise<SubmitResult> {
  return request(`/teach/${sessionId}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      image_base64: imageBase64,
      live_context: liveContext,
      shot_intent: shotIntent ?? null,
    }),
  })
}

export async function teachNext(
  sessionId: string,
): Promise<{ lesson_plan: LessonPlan }> {
  return request(`/teach/${sessionId}/next`, { method: 'POST' })
}

export async function getProfile(name: string): Promise<Profile> {
  return request(`/profiles/${encodeURIComponent(name)}`)
}

export async function listProfiles(): Promise<string[]> {
  return request('/profiles')
}
