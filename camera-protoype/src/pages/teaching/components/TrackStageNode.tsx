interface TrackStageNodeProps {
  stage: number
  label: string
  isPast: boolean
  isHere: boolean
  isFuture: boolean
  isMaxed: boolean
  bobY: number
}

export function TrackStageNode({
  stage,
  label,
  isPast,
  isHere,
  isFuture,
  isMaxed,
  bobY,
}: TrackStageNodeProps) {
  let circleClass = 'border-slate-600 bg-slate-800/90 text-slate-500'
  if (isPast) {
    circleClass =
      'border-emerald-500/60 bg-emerald-600/25 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.25)]'
  } else if (isHere) {
    circleClass = isMaxed
      ? 'scale-110 border-amber-500/80 bg-amber-600/30 text-amber-200 shadow-lg shadow-amber-500/20 ring-2 ring-amber-500/30'
      : 'scale-110 border-indigo-400 bg-indigo-600/40 text-white shadow-lg shadow-indigo-600/40 ring-2 ring-indigo-500/30'
  }

  let labelClass = 'text-slate-600'
  if (isPast) labelClass = 'text-slate-400'
  if (isHere) labelClass = isMaxed ? 'text-amber-300' : 'text-indigo-300'

  return (
    <li
      className="flex flex-col items-center"
      style={{ transform: `translateY(${bobY}px)` }}
    >
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300 ${circleClass}`}
      >
        {isFuture ? '−' : isHere ? (isMaxed ? '★' : stage) : '✓'}
      </div>
      <span className={`mt-2 max-w-[4.2rem] text-center text-[10px] font-medium leading-tight ${labelClass}`}>
        {label}
      </span>
    </li>
  )
}
