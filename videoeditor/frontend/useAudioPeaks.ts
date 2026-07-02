import { useEffect, useRef, useState } from "react"
import type { AudioPeaks, AudioTrack } from "./types"
import { videoeditorApi } from "./api"

/**
 * Lädt Wellenform-Peaks für alle Audio-Clips.
 * AudioClip trägt nur source_rel (Backend-Modell ist fix). Die audio_id
 * (= sha256[:32] von source_rel, serverseitig vergeben) kommt aus einem
 * einmaligen audioBrowse() beim Mount → Map source_rel→audio_id.
 * Für jeden Clip mit bekannter audio_id werden die Peaks einmal geholt und
 * unter clipId gecacht. Fehlt die audio_id (Datei weg / nicht aufbereitet),
 * bleibt der Clip ohne Waveform (drawAudioTrack zeichnt dann Platzhalter).
 */
export function useAudioPeaks(projectId: string, tracks: AudioTrack[]) {
  const [peaksByClipId, setPeaks] = useState<Record<string, AudioPeaks | undefined>>({})
  const idBySource = useRef<Map<string, string>>(new Map())
  const inflight = useRef<Set<string>>(new Set())        // audio_ids die gerade laden
  const peaksByAudioId = useRef<Map<string, AudioPeaks>>(new Map())
  const [browsed, setBrowsed] = useState(false)

  // Einmalig source_rel→audio_id auflösen.
  useEffect(() => {
    let alive = true
    videoeditorApi.audioBrowse(projectId)
      .then((entries) => {
        if (!alive) return
        const m = new Map<string, string>()
        for (const e of entries) if (e.audio_id) m.set(e.source_rel, e.audio_id)
        idBySource.current = m
        setBrowsed(true)
      })
      .catch(() => { if (alive) setBrowsed(true) })
    return () => { alive = false }
  }, [projectId])

  // Für jeden sichtbaren Clip Peaks nachladen (deduped über audio_id).
  useEffect(() => {
    if (!browsed) return
    for (const track of tracks) {
      for (const clip of track.clips) {
        if (peaksByClipId[clip.id]) continue
        const audioId = idBySource.current.get(clip.source_rel)
        if (!audioId) continue

        const cached = peaksByAudioId.current.get(audioId)
        if (cached) { setPeaks((p) => ({ ...p, [clip.id]: cached })); continue }
        if (inflight.current.has(audioId)) continue

        inflight.current.add(audioId)
        const capturedClipId = clip.id
        videoeditorApi.audioPeaks(projectId, audioId)
          .then((pk) => {
            peaksByAudioId.current.set(audioId, pk)
            setPeaks((p) => ({ ...p, [capturedClipId]: pk }))
          })
          .catch(() => {})
          .finally(() => { inflight.current.delete(audioId) })
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [browsed, tracks, projectId])

  return peaksByClipId
}
