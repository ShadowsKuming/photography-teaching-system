import { useCallback, useEffect, useRef, useState } from 'react'
import { Capacitor } from '@capacitor/core'
import { Camera as CapCamera, CameraResultType, CameraSource } from '@capacitor/camera'
import type { TargetSkill } from '../types'
import { buildMinimalLiveCtx } from '../types'

interface Props {
  targetSkill: TargetSkill
  onCapture: (imageBase64: string, liveCtx: ReturnType<typeof buildMinimalLiveCtx>) => void
  onCancel: () => void
}

const isNative = Capacitor.isNativePlatform()

// ── Skill-specific rotating tips ─────────────────────────────────────────────
const SKILL_TIPS: Record<TargetSkill, string[]> = {
  composition: [
    'Place your subject on a grid line',
    'Leave breathing room in the direction they face',
    'Try a different angle or distance',
  ],
  lighting: [
    'Watch for harsh shadows on your subject',
    'Soft, diffused light flatters most subjects',
    'Avoid shooting directly into a bright window',
  ],
  subject_clarity: [
    'Create distance between subject and background',
    'Get closer to fill the frame with your subject',
    'Focus on your subject\'s eyes',
  ],
  pose_expression: [
    'Ask your subject to relax their shoulders',
    'Try a slight turn — avoid facing straight-on',
    'Wait for a natural, candid moment',
  ],
  background_control: [
    'Check what\'s directly behind your subject',
    'Move to a cleaner, simpler background',
    'Look for distracting lines or objects',
  ],
}

// Maps a cue to the backend EventDetail value it corresponds to
const CUE_TO_DETAIL: Record<string, string> = {
  tilt:        'straighten_frame',
  dark:        'move_to_better_light',
  bright:      'move_to_better_light',
  composition: 'reposition_subject',
  lighting:    'move_to_better_light',
  subject_clarity:    'reposition_subject',
  pose_expression:    'adjust_pose',
  background_control: 'simplify_background',
}

type CueSource = 'tilt' | 'brightness' | 'tip'

interface ActiveCue {
  text: string
  source: CueSource
  detail: string
}

export function Camera({ targetSkill, onCapture, onCancel }: Props) {
  const videoRef      = useRef<HTMLVideoElement>(null)
  const streamRef     = useRef<MediaStream | null>(null)
  const tipIndexRef   = useRef(0)
  const cuesShownRef  = useRef<string[]>([])    // tracks which cues appeared (for live ctx)

  const [cue, setCue]           = useState<ActiveCue | null>(null)
  const [tiltAngle, setTiltAngle] = useState(0)
  const [showGrid, setShowGrid] = useState(true)

  // ── Stream management ─────────────────────────────────────────────────────
  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  // Start web camera
  useEffect(() => {
    if (isNative) return
    let cancelled = false
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then((stream) => {
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          void videoRef.current.play()
        }
      })
      .catch(() => {})
    return () => { cancelled = true; stopStream() }
  }, [stopStream])

  // Native camera: open immediately, no custom UI needed
  useEffect(() => {
    if (!isNative) return
    CapCamera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: CameraResultType.Base64,
      source: CameraSource.Camera,
    })
      .then((photo) => {
        if (photo.base64String) onCapture(photo.base64String, buildMinimalLiveCtx(targetSkill))
        else onCancel()
      })
      .catch(() => onCancel())
  }, [targetSkill, onCapture, onCancel])

  // ── Tilt detection via device orientation ─────────────────────────────────
  useEffect(() => {
    if (isNative) return
    const handler = (e: DeviceOrientationEvent) => {
      const gamma = e.gamma ?? 0   // left/right tilt in degrees
      setTiltAngle(gamma)
    }
    window.addEventListener('deviceorientation', handler)
    return () => window.removeEventListener('deviceorientation', handler)
  }, [])

  // ── Brightness analysis (every 1.5 s) ────────────────────────────────────
  useEffect(() => {
    if (isNative) return
    const id = setInterval(() => {
      const video = videoRef.current
      if (!video || !video.videoWidth) return
      const canvas = document.createElement('canvas')
      canvas.width = 40; canvas.height = 40
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(video, 0, 0, 40, 40)
      const px = ctx.getImageData(0, 0, 40, 40).data
      let sum = 0
      for (let i = 0; i < px.length; i += 4)
        sum += (px[i] + px[i + 1] + px[i + 2]) / 3
      const brightness = sum / (40 * 40)

      if (brightness < 45) {
        const text = 'Scene is very dark — move to better light'
        cuesShownRef.current.push('dark')
        setCue({ text, source: 'brightness', detail: CUE_TO_DETAIL.dark })
      } else if (brightness > 215) {
        const text = 'Very bright — avoid shooting into light'
        cuesShownRef.current.push('bright')
        setCue({ text, source: 'brightness', detail: CUE_TO_DETAIL.bright })
      }
    }, 1500)
    return () => clearInterval(id)
  }, [])

  // ── Tilt cue (updates when tilt changes) ─────────────────────────────────
  useEffect(() => {
    if (isNative) return
    if (Math.abs(tiltAngle) > 8) {
      const dir = tiltAngle > 0 ? 'right' : 'left'
      cuesShownRef.current.push('tilt')
      setCue({
        text: `Camera tilting ${dir} — straighten your frame`,
        source: 'tilt',
        detail: CUE_TO_DETAIL.tilt,
      })
    }
  }, [tiltAngle])

  // ── Rotating skill tips (every 5 s) ──────────────────────────────────────
  useEffect(() => {
    if (isNative) return
    const tips = SKILL_TIPS[targetSkill]

    // Show first tip immediately
    setCue({ text: tips[0], source: 'tip', detail: CUE_TO_DETAIL[targetSkill] })
    cuesShownRef.current.push(targetSkill)

    const id = setInterval(() => {
      tipIndexRef.current = (tipIndexRef.current + 1) % tips.length
      setCue({
        text: tips[tipIndexRef.current],
        source: 'tip',
        detail: CUE_TO_DETAIL[targetSkill],
      })
      cuesShownRef.current.push(targetSkill)
    }, 5000)
    return () => clearInterval(id)
  }, [targetSkill])

  // ── Capture ───────────────────────────────────────────────────────────────
  const captureFrame = useCallback(() => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    const base64 = canvas.toDataURL('image/jpeg', 0.92).split(',')[1]
    stopStream()
    onCapture(base64, buildMinimalLiveCtx(targetSkill))
  }, [targetSkill, onCapture, stopStream])

  const handleCancel = useCallback(() => { stopStream(); onCancel() }, [stopStream, onCancel])

  // ── Native: waiting screen ────────────────────────────────────────────────
  if (isNative) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
        <p className="text-sm text-white/60">Opening camera…</p>
      </div>
    )
  }

  const tiltBadgeVisible = Math.abs(tiltAngle) > 3

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black" role="dialog" aria-modal="true">

      {/* ── Top bar: X close + skill label + grid toggle ── */}
      <div
        className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-4 py-3"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        {/* X close button — always visible, top-left */}
        <button
          type="button"
          onClick={handleCancel}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur-sm transition hover:bg-black/80 active:scale-90"
          aria-label="Close camera"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 2l12 12M14 2L2 14" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>

        {/* Skill label — center */}
        <div className="rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm capitalize">
          {targetSkill.replace(/_/g, ' ')}
        </div>

        {/* Grid toggle — top-right */}
        <button
          type="button"
          onClick={() => setShowGrid((v) => !v)}
          className={`flex h-9 w-9 items-center justify-center rounded-full backdrop-blur-sm transition active:scale-90 ${
            showGrid ? 'bg-white/30 text-white' : 'bg-black/60 text-white/50'
          }`}
          aria-label="Toggle grid"
          title="Toggle rule of thirds"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <line x1="5.33" y1="0" x2="5.33" y2="16" stroke="currentColor" strokeWidth="1.2"/>
            <line x1="10.67" y1="0" x2="10.67" y2="16" stroke="currentColor" strokeWidth="1.2"/>
            <line x1="0" y1="5.33" x2="16" y2="5.33" stroke="currentColor" strokeWidth="1.2"/>
            <line x1="0" y1="10.67" x2="16" y2="10.67" stroke="currentColor" strokeWidth="1.2"/>
          </svg>
        </button>
      </div>

      {/* ── Video feed ── */}
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        playsInline
        autoPlay
        muted
      />

      {/* ── Rule-of-thirds grid overlay ── */}
      {showGrid && (
        <div className="pointer-events-none absolute inset-0 z-10">
          {/* Vertical lines */}
          <div className="absolute inset-y-0 left-1/3 w-px bg-white/25" />
          <div className="absolute inset-y-0 left-2/3 w-px bg-white/25" />
          {/* Horizontal lines */}
          <div className="absolute inset-x-0 top-1/3 h-px bg-white/25" />
          <div className="absolute inset-x-0 top-2/3 h-px bg-white/25" />
          {/* Intersection dots */}
          {[[1,1],[1,2],[2,1],[2,2]].map(([r,c]) => (
            <div
              key={`${r}${c}`}
              className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/50"
              style={{ top: `${r * 33.33}%`, left: `${c * 33.33}%` }}
            />
          ))}
        </div>
      )}

      {/* ── Tilt level indicator ── */}
      {tiltBadgeVisible && (
        <div className="pointer-events-none absolute inset-x-0 top-1/2 z-10 flex justify-center">
          <div className="rounded-full bg-black/60 px-3 py-1 text-[11px] font-medium text-amber-300 backdrop-blur-sm">
            {tiltAngle > 0 ? '← ' : '→ '}
            Tilted {Math.abs(tiltAngle).toFixed(0)}°
          </div>
        </div>
      )}

      {/* ── Live cue text — bottom of video, above controls ── */}
      {cue && (
        <div className="pointer-events-none absolute inset-x-0 bottom-28 z-10 flex justify-center px-6"
          style={{ bottom: 'calc(7rem + env(safe-area-inset-bottom))' }}
        >
          <div
            className={`rounded-xl px-4 py-2 text-xs font-medium text-white backdrop-blur-sm ${
              cue.source === 'brightness' ? 'bg-amber-600/80' :
              cue.source === 'tilt'       ? 'bg-rose-600/80'  :
                                            'bg-black/60'
            }`}
          >
            {cue.source === 'tip'        ? '💡 ' :
             cue.source === 'brightness' ? '⚡ ' : '⚠ '}
            {cue.text}
          </div>
        </div>
      )}

      {/* ── Bottom controls: capture button, truly centered ── */}
      <div
        className="absolute inset-x-0 bottom-0 z-20 flex w-full justify-center bg-gradient-to-t from-black/80 to-transparent py-6"
        style={{ paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}
      >
        <button
          type="button"
          onClick={captureFrame}
          className="relative h-20 w-20 rounded-full border-4 border-white bg-white/20 shadow-xl ring-4 ring-white/20 transition hover:scale-105 active:scale-95"
          aria-label="Take photo"
        >
          {/* Inner circle — absolutely centered, not flex-dependent */}
          <span className="absolute inset-0 m-3 rounded-full bg-white" />
        </button>
      </div>
    </div>
  )
}
