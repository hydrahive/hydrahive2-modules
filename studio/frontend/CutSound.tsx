import { useEffect, useRef } from "react"
import { fileUrl } from "@/shared/files"
import { fileOf } from "./planLogic"
import { setGain } from "./audioGraph"
import { clipGain, voiceSpans, type Mixer } from "./mixLogic"
import { needsSeek, soundTarget } from "./soundLogic"
import type { TimelineClip, TrackId } from "./timelineApi"

interface Props { voice: TimelineClip[]; music: TimelineClip[]; mixer: Mixer; base: string; time: number; playing: boolean; rate: number }

/** Ton der Tonspuren in der Vorschau: je Spur ein unsichtbares <audio>, das der Film-Uhr folgt (Spec 5a „Abspielen“),
 *  mit Lautstärke, Blenden und Ducking aus dem Mischpult (5b). */
export function CutSound({ voice, music, mixer, base, time, playing, rate }: Props) {
  const spans = voiceSpans(mixer, voice)
  return <>
    <SoundLane track="A1" clips={voice} mixer={mixer} spans={spans} base={base} time={time} playing={playing} rate={rate} />
    <SoundLane track="A2" clips={music} mixer={mixer} spans={spans} base={base} time={time} playing={playing} rate={rate} />
  </>
}

function SoundLane({ track, clips, mixer, spans, base, time, playing, rate }: { track: TrackId; clips: TimelineClip[]; mixer: Mixer;
  spans: [number, number][]; base: string; time: number; playing: boolean; rate: number }) {
  const el = useRef<HTMLAudioElement | null>(null)
  const target = soundTarget(clips, time)
  const level = target ? clipGain(mixer, track, target.clip, time, spans) : 0
  useEffect(() => { setGain(el.current, track, level) }, [track, level, target?.clip.id])
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
