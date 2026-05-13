import { useEffect, useState } from 'react'
import * as api from '../api/client'
import type { LeaderboardEntry, PrimarySubject } from '../types'
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'

const SUBJECT_LABEL: Record<PrimarySubject, string> = {
  portrait: 'Portrait',
  scene: 'Scene',
  object: 'Object',
}

const MEDAL: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }

interface Props {
  open: boolean
  subject: PrimarySubject
  studentName: string
  dailyXp: number
  onClose: () => void
}

export function LeaderboardDrawer({ open, subject, studentName, dailyXp, onClose }: Props) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [date, setDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    api
      .getLeaderboard(subject)
      .then((res) => {
        setEntries(res.entries)
        setDate(res.date)
      })
      .catch(() => setError('Could not load leaderboard.'))
      .finally(() => setLoading(false))
  }, [open, subject])

  // Ensure current student appears even if they haven't been ranked yet
  const myEntry = entries.find((e) => e.name === studentName)
  const showMyEntry = !myEntry && dailyXp > 0

  return (
    <Drawer open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <DrawerContent
        aria-label="Daily leaderboard"
        className="border-slate-800 bg-slate-950 text-white"
        style={{ paddingTop: 'env(safe-area-inset-top)', maxHeight: 'calc(100dvh - 1.5rem)' }}
      >
        <DrawerHeader className="px-5 pt-2 pb-0 text-left md:text-left">
          <div className="flex items-center justify-between">
            <DrawerTitle className="text-sm font-semibold text-slate-100">
              {SUBJECT_LABEL[subject]} Leaderboard
            </DrawerTitle>
            <DrawerClose asChild>
              <button
                type="button"
                className="rounded-full px-3 py-1.5 text-xs font-medium text-indigo-300 transition hover:text-white active:scale-95"
              >
                Done
              </button>
            </DrawerClose>
          </div>
          <DrawerDescription className="mt-1 text-[11px] text-slate-500">
            {date ? `Today · ${date}` : 'Today'} · Resets at midnight
          </DrawerDescription>
        </DrawerHeader>

        <div
          className="flex-1 overflow-y-auto px-5 pb-10 pt-4"
          style={{ paddingBottom: 'max(2.5rem, env(safe-area-inset-bottom))' }}
        >
          <div className="mx-auto max-w-xl">
            {loading && (
              <p className="animate-pulse py-8 text-center text-sm text-slate-500">Loading…</p>
            )}

            {error && (
              <p className="py-8 text-center text-sm text-red-400">{error}</p>
            )}

            {!loading && !error && entries.length === 0 && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
                <p className="text-2xl">📷</p>
                <p className="mt-2 text-sm font-medium text-slate-300">No shots yet today</p>
                <p className="mt-1 text-xs text-slate-500">Be the first to earn XP!</p>
              </div>
            )}

            {!loading && !error && entries.length > 0 && (
              <ol className="space-y-2">
                {entries.map((entry) => {
                  const isMe = entry.name === studentName
                  return (
                    <li
                      key={entry.rank}
                      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
                        isMe
                          ? 'border-indigo-600/60 bg-indigo-950/50'
                          : 'border-slate-800 bg-slate-900/60'
                      }`}
                    >
                      <span className="w-7 shrink-0 text-center text-base" aria-label={`Rank ${entry.rank}`}>
                        {MEDAL[entry.rank] ?? (
                          <span className="text-xs font-bold text-slate-500">{entry.rank}</span>
                        )}
                      </span>
                      <span className={`flex-1 truncate text-sm font-medium ${isMe ? 'text-indigo-200' : 'text-slate-200'}`}>
                        {entry.name}
                        {isMe && (
                          <span className="ml-2 rounded-full bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-indigo-300">
                            You
                          </span>
                        )}
                      </span>
                      <span className={`shrink-0 text-sm font-semibold ${isMe ? 'text-amber-300' : 'text-amber-400/80'}`}>
                        {entry.daily_xp} XP
                      </span>
                    </li>
                  )
                })}
              </ol>
            )}

            {/* Show the student's own entry below the list if not yet ranked */}
            {showMyEntry && (
              <div className="mt-3 rounded-2xl border border-indigo-600/40 bg-indigo-950/30 px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Your progress today</p>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm font-medium text-indigo-200">
                    {studentName}
                    <span className="ml-2 rounded-full bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-indigo-300">
                      You
                    </span>
                  </span>
                  <span className="text-sm font-semibold text-amber-300">{dailyXp} XP</span>
                </div>
              </div>
            )}

            <p className="mt-6 text-center text-[11px] text-slate-600">
              XP = photos taken × quality. Max 10 XP per shot.
            </p>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  )
}
