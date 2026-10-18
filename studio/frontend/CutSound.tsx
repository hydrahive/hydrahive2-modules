import { useEffect, useRef } from "react"
import { fileUrl } from "@/shared/files"
import { fileOf } from "./planLogic"
import { needsSeek, soundTarget } from "./soundLogic"
import type { TimelineClip } from "./timelineApi"

/** Ton der Tonspuren in der Vorschau: je Spur ein unsichtbares <audio>, das der Film-Uhr folgt (Spec 5a „Abspielen“). */
export function CutSound({ tracks, base, time, playing, rate }: { tracks: TimelineClip[][]; base: string; time: number; playing: boolean; rate: number }) {
  return <>{tracks.map((clips, i) => <SoundLane key={i} clips={clips} base={base} time={time} playing={playing} rate={rate} />)}</>
}

function SoundLane({ clips, base, time, playing, rate }: { clips: TimelineClip[]; base: string; time: number; playing: boolean; rate: number }) {
  const el = useRef<HTMLAudioElement | null>(null)
  const target = soundTarget(clips, time)
  useEffect(() => {
    const a = el.current
    if (!a || !target) return
    if (needsSeek(a.currentTime, target.at, playing)) {
      try { a.currentTime = target.at } catch { /* Metadaten noch nicht da */ }
    }
    a.playbackRate = rate
    if (playing && a.paused) a.play().catch(() => {})
    if (!playing && !a.paused) a.pause()
  }, [target, playing, rate])
  if (!target) return null
  return <audio key={target.clip.id} ref={el} src={fileUrl(fileOf(base, target.clip.media_rel))} preload="auto" data-cut-sound={target.clip.id} />
}
