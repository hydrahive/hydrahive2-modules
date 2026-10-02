// Reine Playlist-Logik nach Track-ID (ohne React, testbar).
// ID statt Position: Neue Einträge kommen vorne dazu (Liste nach Datum absteigend).
// Mit einer Position würde jeder Import das laufende Lied wechseln.

export type RepeatMode = "off" | "all" | "one"
export interface Order { shuffle: boolean; random: () => number }
export type EndAction = { kind: "repeat" } | { kind: "stop" } | { kind: "play"; id: number }

type WithId = { id: number }

export function currentOf<T extends WithId>(tracks: T[], id: number | null): T | null {
  if (id === null) return null
  return tracks.find((track) => track.id === id) ?? null
}

function shuffled(tracks: WithId[], pos: number, random: () => number): number {
  let r = pos
  while (r === pos) r = Math.floor(random() * tracks.length)
  return tracks[r].id
}

export function nextId(tracks: WithId[], id: number | null, order: Order): number | null {
  if (tracks.length === 0) return null
  const pos = tracks.findIndex((track) => track.id === id)
  if (pos < 0) return tracks[0].id
  if (order.shuffle && tracks.length > 1) return shuffled(tracks, pos, order.random)
  return tracks[(pos + 1) % tracks.length].id
}

export function prevId(tracks: WithId[], id: number | null, order: Order): number | null {
  if (tracks.length === 0) return null
  const pos = tracks.findIndex((track) => track.id === id)
  if (pos < 0) return tracks[0].id
  if (order.shuffle && tracks.length > 1) return shuffled(tracks, pos, order.random)
  return tracks[pos <= 0 ? tracks.length - 1 : pos - 1].id
}

export function afterEnded(tracks: WithId[], id: number | null, repeat: RepeatMode, order: Order): EndAction {
  const pos = tracks.findIndex((track) => track.id === id)
  if (pos < 0) return { kind: "stop" }
  if (repeat === "one") return { kind: "repeat" }
  if (repeat === "off" && !order.shuffle && pos === tracks.length - 1) return { kind: "stop" }
  const next = nextId(tracks, id, order)
  return next === null ? { kind: "stop" } : { kind: "play", id: next }
}
