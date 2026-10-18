import { SubtitleInspector, ReplaceDialog } from "./SubtitleArea"
import { SubtitleList } from "./SubtitleList"
import { SubtitleOverlay } from "./SubtitleOverlay"
import { SubtitleTrack } from "./SubtitleTrack"
import type { Plan } from "./planApi"
import type { Viewport } from "./timeline"
import type { useSubtitles } from "./useSubtitles"

type Sub = ReturnType<typeof useSubtitles>

/** Reiter „Untertitel“ (Spec 6a): Teile für die festen Bereiche des Studios (links, Vorschau, rechts, unten). */
function subtitlePanels(sub: Sub, o: { time: number; view: Viewport; hasSpeech: boolean; onSeek: (t: number) => void }) {
  const pick = (id: string) => { sub.select(id); const c = sub.cues.find((x) => x.id === id); if (c) o.onSeek(c.start) }
  return {
    left: <SubtitleList cues={sub.cues} selected={sub.selected} time={o.time} hasSpeech={o.hasSpeech} busy={sub.busy} save={sub.save}
      canUndo={sub.canUndo} canRedo={sub.canRedo} onSelect={pick} onChange={sub.changeText} onAction={sub.action}
      onFromSpeech={sub.fromSpeech} onExport={sub.exportFile} />,
    overlay: <SubtitleOverlay cues={sub.cues} time={o.time} />,
    right: <SubtitleInspector cue={sub.cues.find((c) => c.id === sub.selected) ?? null} onTime={sub.setTime} />,
    track: <SubtitleTrack cues={sub.cues} view={o.view} time={o.time} selected={sub.selected} onSelect={sub.select} onSeek={o.onSeek} />,
    dialog: sub.confirm ? <ReplaceDialog count={sub.cues.length} busy={sub.busy} onConfirm={sub.confirmReplace} onClose={sub.closeConfirm} /> : null,
  }
}

/** Alles für den Reiter „Untertitel“ gebündelt (StudioPage bleibt klein): Hook, Bereiche, Tasten. */
export function useSubtitleTab(sub: Sub, opts: { time: number; view: Viewport; plan: Plan | null; onSeek: (t: number) => void }) {
  const hasSpeech = !!opts.plan?.scenes.some((sc) => sc.shots.some((x) => (x.speech ?? "").trim()))
  const o = { ...opts, hasSpeech }
  const keys = (a: string): boolean => {
    const map: Record<string, "undo" | "redo" | "split" | "delete"> = { undo: "undo", redo: "redo", split: "split", delete: "delete" }
    if (!map[a]) return false
    sub.action(map[a])
    return true
  }
  return { ...subtitlePanels(sub, o), keys }
}
