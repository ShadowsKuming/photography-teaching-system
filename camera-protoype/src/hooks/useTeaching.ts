import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api/client'
import type { LessonPlan, LiveContextInput, Profile, SubmitResult } from '../types'

export interface UseTeachingReturn {
  profile: Profile | null
  lessonPlan: LessonPlan | null
  result: SubmitResult | null
  isLoading: boolean
  error: string | null
  submitPhoto: (imageBase64: string, liveCtx: LiveContextInput, shotIntent?: string) => Promise<void>
  nextLesson: () => Promise<void>
  clearResult: () => void
}

export function useTeaching(studentName: string): UseTeachingReturn {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [lessonPlan, setLessonPlan] = useState<LessonPlan | null>(null)
  const [result, setResult] = useState<SubmitResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!studentName) return
    setIsLoading(true)
    setError(null)
    api
      .teachStart(studentName)
      .then((res) => {
        sessionIdRef.current = res.session_id
        setProfile(res.profile)
        setLessonPlan(res.lesson_plan)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false))
  }, [studentName])

  const submitPhoto = useCallback(
    async (imageBase64: string, liveCtx: LiveContextInput, shotIntent?: string) => {
      if (!sessionIdRef.current) return
      setIsLoading(true)
      setError(null)
      try {
        const res = await api.teachSubmit(
          sessionIdRef.current,
          imageBase64,
          liveCtx,
          shotIntent,
        )
        setResult(res)
        // Update local skill display
        if (profile) {
          setProfile((prev) =>
            prev
              ? {
                  ...prev,
                  milestone: res.current_milestone,
                  skill_state: Object.fromEntries(
                    Object.entries(prev.skill_state).map(([k, v]) => [
                      k,
                      { ...v, level: res.updated_skill_levels[k as keyof typeof res.updated_skill_levels] ?? v.level },
                    ]),
                  ) as Profile['skill_state'],
                }
              : prev,
          )
        }
      } catch (e) {
        setError(String(e))
      } finally {
        setIsLoading(false)
      }
    },
    [profile],
  )

  const nextLesson = useCallback(async () => {
    if (!sessionIdRef.current) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.teachNext(sessionIdRef.current)
      setLessonPlan(res.lesson_plan)
      setResult(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearResult = useCallback(() => setResult(null), [])

  return { profile, lessonPlan, result, isLoading, error, submitPhoto, nextLesson, clearResult }
}
