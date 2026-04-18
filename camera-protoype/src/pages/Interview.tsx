import { useEffect, useRef, useState } from 'react'
import { ChatBubble } from '../components/ChatBubble'
import { StyleGrid } from '../components/StyleGrid'
import { useInterview } from '../hooks/useInterview'
import type { Profile, StyleName } from '../types'

interface Props {
  onComplete: (profile: Profile) => void
}

type InputMode = 'chat' | 'name'

export function Interview({ onComplete }: Props) {
  const {
    messages, interviewState, isLoading, error,
    showStyleGrid, profile,
    start, send, selectStyles, submitName, finalise,
  } = useInterview()

  const [inputMode, setInputMode] = useState<InputMode>('chat')
  const [text, setText] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const startedRef = useRef(false)

  // Start interview once
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    void start()
  }, [start])

  // Switch to name input when agent asks for name
  useEffect(() => {
    if (interviewState === 'naming') setInputMode('name')
  }, [interviewState])

  // Auto-finalise when conversation completes
  useEffect(() => {
    if (interviewState === 'complete' && !profile) void finalise()
  }, [interviewState, profile, finalise])

  // Transition to teaching when profile is ready
  useEffect(() => {
    if (profile) onComplete(profile)
  }, [profile, onComplete])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, showStyleGrid])

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    setText('')
    if (inputMode === 'name') {
      void submitName(trimmed)
    } else {
      void send(trimmed)
    }
  }

  const handleStyleConfirm = (styles: StyleName[]) => {
    void selectStyles(styles)
  }

  return (
    <div className="flex min-h-dvh flex-col bg-slate-950 text-white">
      {/* Header */}
      <header
        className="shrink-0 border-b border-slate-800 bg-slate-900/80 px-4 py-3 backdrop-blur-md"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📷</span>
          <div>
            <p className="text-xs font-medium text-indigo-400">Photography Coach</p>
            <p className="text-sm font-semibold">Getting to know you</p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto max-w-xl space-y-3">
          {messages.map((m, i) => (
            <ChatBubble key={i} role={m.role} content={m.content} />
          ))}

          {/* Style grid inline */}
          {showStyleGrid && (
            <div className="mt-2">
              <StyleGrid onConfirm={handleStyleConfirm} isLoading={isLoading} />
            </div>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-slate-800 px-4 py-2.5 text-sm text-slate-400">
                <span className="animate-pulse">●●●</span>
              </div>
            </div>
          )}

          {error && (
            <p className="text-center text-xs text-red-400">{error}</p>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input */}
      <div
        className="shrink-0 border-t border-slate-800 bg-slate-900/80 px-4 py-3 backdrop-blur-md"
        style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
      >
        <div className="mx-auto flex max-w-xl gap-2">
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={inputMode === 'name' ? 'Enter your first name…' : 'Type a message…'}
            disabled={isLoading || showStyleGrid}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-40"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!text.trim() || isLoading || showStyleGrid}
            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
