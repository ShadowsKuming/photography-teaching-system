import { useCallback, useRef, useState } from 'react'
import * as api from '../api/client'
import type { ChatMessage, InterviewState, Profile, StyleName } from '../types'
import type { AppLocale } from '../i18n'

export interface UseInterviewReturn {
  messages: ChatMessage[]
  interviewState: InterviewState
  isLoading: boolean
  error: string | null
  showStyleGrid: boolean
  profile: Profile | null
  sessionId: string | null
  // actions
  start: () => Promise<void>
  send: (message: string) => Promise<void>
  selectStyles: (styles: StyleName[]) => Promise<void>
  submitName: (name: string) => Promise<void>
  finalise: () => Promise<void>
}

export function useInterview(locale: AppLocale): UseInterviewReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [interviewState, setInterviewState] = useState<InterviewState>('chatting')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showStyleGrid, setShowStyleGrid] = useState(false)
  const [profile, setProfile] = useState<Profile | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  const pushAssistant = (content: string) =>
    setMessages((prev) => [...prev, { role: 'assistant', content }])

  const pushUser = (content: string) =>
    setMessages((prev) => [...prev, { role: 'user', content }])

  const start = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.interviewStart(locale)
      sessionIdRef.current = res.session_id
      pushAssistant(res.opening_message)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [locale])

  const send = useCallback(async (message: string) => {
    if (!sessionIdRef.current) return
    pushUser(message)
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.interviewChat(sessionIdRef.current, message, locale)
      pushAssistant(res.reply)
      setInterviewState(res.state as InterviewState)
      if (res.show_style_grid) setShowStyleGrid(true)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [locale])

  const selectStyles = useCallback(async (styles: StyleName[]) => {
    if (!sessionIdRef.current) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.interviewStyle(sessionIdRef.current, styles, locale)
      pushAssistant(res.reply)
      setInterviewState(res.state as InterviewState)
      setShowStyleGrid(false)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [locale])

  const submitName = useCallback(async (name: string) => {
    if (!sessionIdRef.current) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.interviewName(sessionIdRef.current, name, locale)
      pushAssistant(res.reply)
      if (res.is_complete) setInterviewState('complete')
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [locale])

  const finalise = useCallback(async () => {
    if (!sessionIdRef.current) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.interviewComplete(sessionIdRef.current)
      localStorage.setItem('student_id', res.student_id)
      localStorage.setItem('student_name', res.profile.name)
      setProfile(res.profile)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    messages,
    interviewState,
    isLoading,
    error,
    showStyleGrid,
    profile,
    sessionId: sessionIdRef.current,
    start,
    send,
    selectStyles,
    submitName,
    finalise,
  }
}
