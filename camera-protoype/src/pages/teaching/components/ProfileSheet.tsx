import { useMemo, useState } from 'react'
import type { MilestoneLevel, Profile, TargetSkill } from '../../../types'
import { SKILL_CONTENT, describeCurrentState, describeNextStep } from './skillContent'
import { SKILL_LABELS, STAGE_COUNT } from './trackConfig'
import type { AppLocale } from '../../../i18n'
import { useI18n } from '../../../i18n'
import { LanguageSelector } from '../../../components/LanguageSelector'
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'

interface Props {
  open: boolean
  profile: Profile
  onClose: () => void
  locale: AppLocale
}

const MILESTONE_ORDER: MilestoneLevel[] = ['beginner', 'developing', 'intermediate', 'advanced']
const MILESTONE_LABEL: Record<MilestoneLevel, string> = {
  beginner: 'Beginner',
  developing: 'Developing',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

export function ProfileSheet({ open, profile, onClose, locale }: Props) {
  const { setLocale, copy } = useI18n()
  const skills = useMemo(
    () =>
      (Object.entries(profile.skill_state) as [TargetSkill, { level: number }][])
        .filter(([skill]) =>
          skill !== 'pose_expression' || profile.primary_subject === 'portrait',
        ),
    [profile],
  )

  const milestoneIdx = MILESTONE_ORDER.indexOf(profile.milestone)
  const milestoneProgress =
    milestoneIdx <= 0 ? 0 : (milestoneIdx / (MILESTONE_ORDER.length - 1)) * 100

  return (
    <Drawer
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose()
      }}
    >
      <DrawerContent
        aria-label={copy.profileProgressTitle}
        className="border-slate-800 bg-slate-950 text-white"
        style={{ paddingTop: 'env(safe-area-inset-top)', maxHeight: 'calc(100dvh - 1.5rem)' }}
      >
        <DrawerHeader className="px-5 pt-2 pb-0 text-left md:text-left">
          <div className="flex items-center justify-between">
            <DrawerTitle className="text-sm font-semibold text-slate-100">
              {copy.profileProgressTitle}
            </DrawerTitle>
            <div className="flex items-center gap-2">
              <LanguageSelector locale={locale} onChange={setLocale} />
              <DrawerClose asChild>
                <button
                  type="button"
                  className="rounded-full px-3 py-1.5 text-xs font-medium text-indigo-300 transition hover:text-white active:scale-95"
                >
                  {copy.profileDone}
                </button>
              </DrawerClose>
            </div>
          </div>
          <DrawerDescription className="sr-only">
            {locale === 'pt-BR'
              ? 'Seus marcos de fotografia e niveis de habilidade.'
              : 'Your photography milestones and skill levels.'}
          </DrawerDescription>
        </DrawerHeader>

        <div
          className="flex-1 overflow-y-auto px-5 pb-10 pt-4"
          style={{ paddingBottom: 'max(2.5rem, env(safe-area-inset-bottom))' }}
        >
          <div className="mx-auto max-w-xl">
            <section className="flex items-center gap-4">
              <div
                className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-xl font-bold text-white shadow-lg shadow-indigo-600/30"
                aria-hidden
              >
                {initials(profile.name)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs uppercase tracking-wider text-slate-500">
                  {copy.profilePhotographer}
                </p>
                <p className="truncate text-lg font-semibold text-white">{profile.name}</p>

              </div>
            </section>

            <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {copy.profileMilestonePath}
              </p>
              <ol className="relative mt-3 grid grid-cols-4 gap-1">
                <span
                  className="pointer-events-none absolute left-0 right-0 top-1 h-0.5 bg-slate-700"
                  aria-hidden
                />
                <span
                  className="pointer-events-none absolute left-0 top-1 h-0.5 bg-indigo-500 transition-[width] duration-500"
                  style={{ width: `${milestoneProgress}%` }}
                  aria-hidden
                />
                {MILESTONE_ORDER.map((m, i) => {
                  const reached = i <= milestoneIdx
                  return (
                    <li key={m} className="relative z-[1] flex flex-col items-center">
                      <div className="relative grid h-2 w-full place-items-center">
                        <span
                          className={`-translate-y-[2px] relative z-[1] h-3.5 w-3.5 rounded-full border-2 ${reached
                            ? 'border-indigo-400 bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.6)]'
                            : 'border-slate-600 bg-slate-800'
                            }`}
                          aria-hidden
                        />
                      </div>
                      <span
                        className={`mt-2 text-center text-[10px] font-medium leading-tight ${reached ? 'text-indigo-200' : 'text-slate-500'
                          }`}
                      >
                        {MILESTONE_LABEL[m]}
                      </span>
                    </li>
                  )
                })}
              </ol>
            </section>

            <section className="mt-6">
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {copy.profileSkills}
              </p>
              <div className="space-y-3">
                {skills.map(([skill, { level }]) => (
                  <SkillCard key={skill} skill={skill} level={level} />
                ))}
              </div>
            </section>

            <p className="mt-8 text-center text-[11px] leading-relaxed text-slate-600">
              {copy.profileLevelsHint}
            </p>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  )
}

// ── Skill card ───────────────────────────────────────────────────────────────

interface SkillCardProps {
  skill: TargetSkill
  level: number
}

function SkillCard({ skill, level }: SkillCardProps) {
  const [expanded, setExpanded] = useState(false)
  const content = SKILL_CONTENT[skill]
  const safeLevel = Math.max(0, Math.min(STAGE_COUNT, Math.round(level)))
  const pct = (safeLevel / STAGE_COUNT) * 100
  const currentState = describeCurrentState(skill, safeLevel)
  const next = describeNextStep(skill, safeLevel)
  const isMaxed = safeLevel >= STAGE_COUNT

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-3 px-4 pt-4 pb-3 text-left transition active:scale-[0.99]"
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="truncate text-sm font-semibold text-white">{SKILL_LABELS[skill]}</h3>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${isMaxed
                ? 'bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/30'
                : safeLevel === 0
                  ? 'bg-slate-700/40 text-slate-400 ring-1 ring-inset ring-slate-600/40'
                  : 'bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/30'
                }`}
            >
              Level {safeLevel}/{STAGE_COUNT}
            </span>
          </div>
          <p className="mt-1 text-[11px] leading-snug text-slate-500">{content.blurb}</p>

          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ${isMaxed
                ? 'bg-gradient-to-r from-amber-400 to-amber-500'
                : 'bg-gradient-to-r from-emerald-400 via-indigo-400 to-fuchsia-500'
                }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          <p className="mt-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Where you are
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-200">{currentState}</p>

          {next && (
            <p className="mt-2 text-xs leading-relaxed text-slate-400">{next}</p>
          )}
        </div>

        <span
          className={`mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-180 bg-slate-800 text-white' : 'bg-slate-800/60'
            }`}
          aria-hidden
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>

      {expanded && (
        <div className="border-t border-slate-800 bg-slate-950/40 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Full path
          </p>
          <ol className="mt-2 space-y-2.5">
            {content.levels.map((info, i) => {
              const stage = i + 1
              const isPast = stage < safeLevel
              const isCurrent = stage === safeLevel
              const isLocked = stage > safeLevel
              return (
                <li key={stage} className="flex items-start gap-3">
                  <span
                    className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border text-[11px] font-bold ${isPast
                      ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-300'
                      : isCurrent
                        ? 'border-indigo-400 bg-indigo-500/30 text-white shadow-[0_0_10px_rgba(99,102,241,0.45)]'
                        : 'border-slate-700 bg-slate-800/60 text-slate-500'
                      }`}
                    aria-hidden
                  >
                    {isPast ? '✓' : isLocked ? <LockIcon /> : stage}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <p
                        className={`text-sm font-semibold ${isPast ? 'text-emerald-200' : isCurrent ? 'text-white' : 'text-slate-400'
                          }`}
                      >
                        {info.title}
                      </p>
                      {isCurrent && (
                        <span className="rounded-full bg-indigo-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-indigo-300">
                          You
                        </span>
                      )}
                      {isPast && (
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                          Earned
                        </span>
                      )}
                    </div>
                    <p
                      className={`mt-0.5 text-xs leading-relaxed ${isLocked ? 'text-slate-500' : 'text-slate-300'
                        }`}
                    >
                      {info.gain}
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </article>
  )
}

function LockIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  )
}
