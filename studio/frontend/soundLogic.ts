/** Ton der Tonspuren in der Vorschau (5a): reine Rechenhilfen, damit testbar. */
import { audioAt } from "./cutAudio"
import { sourceTime } from "./cutLogic"
import type { TimelineClip } from "./timelineApi"

/** Abweichung, ab der nachgestellt wird: beim Abspielen großzügig (sonst knackt es), im Stand genau. */
export const DRIFT_PLAYING = 0.15
export const DRIFT_PAUSED = 0.04

/** Soll-Stelle im Tonclip bei Filmzeit t, oder null, wenn auf dieser Spur gerade nichts klingt. */
export function soundTarget(clips: TimelineClip[], t: number): { clip: TimelineClip; at: number } | null {
  const c = audioAt(clips, t)
  return c ? { clip: c, at: sourceTime(c, t) } : null
}

export function needsSeek(current: number, want: number, playing: boolean): boolean {
  return Math.abs(current - want) > (playing ? DRIFT_PLAYING : DRIFT_PAUSED)
}
