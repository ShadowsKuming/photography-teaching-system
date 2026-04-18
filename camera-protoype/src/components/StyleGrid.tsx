import { useState } from 'react'
import type { StyleName } from '../types'

const STYLES: { name: StyleName; description: string; gradient: string }[] = [
  { name: 'Warm & Film',    description: 'Faded, golden — feels like a memory',   gradient: 'from-amber-500 to-yellow-300' },
  { name: 'Clean & Bright', description: 'Sharp, airy, magazine-like',             gradient: 'from-sky-200 to-white' },
  { name: 'Moody & Dark',   description: 'High contrast, dramatic shadows',        gradient: 'from-indigo-950 to-purple-800' },
  { name: 'Documentary',    description: 'Raw, unposed, in-the-moment',            gradient: 'from-gray-500 to-gray-300' },
  { name: 'Soft & Dreamy',  description: 'Gentle light, blurred backgrounds',      gradient: 'from-pink-300 to-rose-100' },
  { name: 'Gritty & Urban', description: 'Harsh light, real textures',             gradient: 'from-stone-700 to-stone-500' },
]

interface Props {
  onConfirm: (selected: StyleName[]) => void
  isLoading?: boolean
}

export function StyleGrid({ onConfirm, isLoading }: Props) {
  const [selected, setSelected] = useState<Set<StyleName>>(new Set())

  const toggle = (name: StyleName) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900">
      <p className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
        Which visual style feels closest to you?
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {STYLES.map((s) => {
          const active = selected.has(s.name)
          return (
            <button
              key={s.name}
              type="button"
              onClick={() => toggle(s.name)}
              className={`relative overflow-hidden rounded-xl border-2 text-left transition ${
                active
                  ? 'border-indigo-500 shadow-md'
                  : 'border-transparent hover:border-slate-300 dark:hover:border-slate-600'
              }`}
            >
              <div className={`h-16 w-full bg-gradient-to-br ${s.gradient}`} />
              <div className="px-2 py-1.5">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{s.name}</p>
                <p className="mt-0.5 text-[10px] leading-tight text-slate-500 dark:text-slate-400">
                  {s.description}
                </p>
              </div>
              {active && (
                <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[9px] text-white">
                  ✓
                </span>
              )}
            </button>
          )
        })}
      </div>
      <button
        type="button"
        disabled={selected.size === 0 || isLoading}
        onClick={() => onConfirm([...selected])}
        className="mt-3 w-full rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40"
      >
        {isLoading ? 'Saving…' : `Confirm ${selected.size > 0 ? `(${selected.size} selected)` : ''}`}
      </button>
    </div>
  )
}
