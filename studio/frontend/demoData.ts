/** Beispieldaten für Zeitleiste und Storyboard, bis Etappe 2 (Planen) und 4 (Schneiden) sie echt machen. */

export type TrackKind = "text" | "video" | "voice" | "music" | "subtitle"

export interface DemoClip {
  id: string
  start: number
  length: number
  label: string
  /** Platzhalter aus dem Drehbuch – noch nicht erzeugt. */
  placeholder?: boolean
  mediaId?: string
}

export interface DemoTrack {
  id: string
  kind: TrackKind
  label: string
  clips: DemoClip[]
}

export const DEMO_DURATION = 90

export const DEMO_TRACKS: DemoTrack[] = [
  { id: "t-text", kind: "text", label: "V2 Text", clips: [{ id: "c1", start: 1, length: 5, label: "Titel: Nordwind" }] },
  {
    id: "t-video", kind: "video", label: "V1 Video", clips: [
      { id: "c2", start: 0, length: 6, label: "Shot 1 – Hafen", mediaId: "m1" },
      { id: "c3", start: 6, length: 8, label: "Shot 2 – Mira", mediaId: "m2" },
      { id: "c4", start: 14, length: 7, label: "Shot 3 – Sturm zieht auf", placeholder: true },
      { id: "c5", start: 21, length: 24, label: "Drohnenflug", mediaId: "m3" },
    ],
  },
  { id: "t-voice", kind: "voice", label: "A1 Sprache", clips: [{ id: "c6", start: 6, length: 12, label: "Dialog Mira", mediaId: "m6" }] },
  { id: "t-music", kind: "music", label: "A2 Musik", clips: [{ id: "c7", start: 0, length: 60, label: "Nordwind", mediaId: "m7" }] },
  {
    id: "t-sub", kind: "subtitle", label: "S1 Untertitel", clips: [
      { id: "c8", start: 6.5, length: 3.5, label: "Wo bist du gewesen?" },
      { id: "c9", start: 10.5, length: 4, label: "Draußen. Der Wind dreht." },
    ],
  },
]

export const DEMO_JOBS = [
  { id: "j1", label: "Video erzeugen: Shot 3", percent: 42 },
  { id: "j2", label: "Proxy: Drohnenflug.mp4", percent: 88 },
]
