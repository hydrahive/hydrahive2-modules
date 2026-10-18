import { useCut } from "./useCut"
import { useCutEdit } from "./useCutEdit"
import { useCutPlayer } from "./useCutPlayer"
import { useWaveforms } from "./useWaveforms"
import { mixerOf, originalGain } from "./mixLogic"
import { allClips } from "./timelineApi"
import type { Workspace } from "./workspaces"

/** „Schneiden“ und „Ton“ arbeiten auf der Schnittfassung (5b). */
export const editing = (w: Workspace): boolean => w === "edit" || w === "audio"
/** Reiter, die den Film abspielen (Schneiden, Ton, Untertitel). */
export const filmWs = (w: Workspace): boolean => editing(w) || w === "subtitles"

/** Schnittfassung, Wiedergabe (mit Mischpult), Wellenformen und Bearbeiten – gebündelt für StudioPage. */
export function useCutWorkspace(projectId: string, workspace: Workspace) {
  const cut = useCut(projectId, filmWs(workspace) || workspace === "deliver")   // „Untertitel“ und „Ausgabe“ brauchen sie auch
  const every = allClips(cut.timeline)
  const mixer = mixerOf(cut.timeline)
  const cp = useCutPlayer(cut.clips, every, originalGain(mixer))
  const waves = useWaveforms(projectId, editing(workspace) ? every : [])
  const ed = useCutEdit(projectId, cut.timeline, cut.setTimeline, cut.selected, cut.select, cp.time, waves.lengths)
  return { cut, every, mixer, cp, waves, ed }
}
