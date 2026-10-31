import { useCallback, useEffect, useState } from "react"
import { getMixes, getPlaylists, getProgram } from "./api"
import type { Mix, Playlist, Program } from "./programLogic"

/** Programm, Playlisten und Mixe laden (Reiter Programm, Sender, Bibliothek teilen sich das). */
export function useProgramData() {
  const [program, setProgram] = useState<Program | null>(null)
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [mixes, setMixes] = useState<Mix[]>([])
  const reload = useCallback(() => {
    getProgram().then(setProgram).catch(() => {})
    getPlaylists().then((r) => setPlaylists(r.items)).catch(() => {})
    getMixes().then((r) => setMixes(r.items)).catch(() => {})
  }, [])
  useEffect(() => { reload() }, [reload])
  return { program, playlists, mixes, reload }
}
