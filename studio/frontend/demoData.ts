/** Beispieldaten der Attrappe (Etappe 0). Ab Etappe 1 kommen sie aus dem Backend. */

export type MediaKind = "video" | "image" | "audio" | "music" | "element"
export type Origin = "ai" | "upload" | "legacy"

export interface DemoMedia {
  id: string
  kind: MediaKind
  name: string
  origin: Origin
  duration?: number
  /** Farbe des Vorschaubilds (Attrappe statt echter Thumbnails). */
  hue: number
}

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

export const DEMO_MEDIA: DemoMedia[] = [
  { id: "m1", kind: "video", name: "Shot 1 – Morgen am Hafen", origin: "ai", duration: 6, hue: 200 },
  { id: "m2", kind: "video", name: "Shot 2 – Mira am Steg", origin: "ai", duration: 8, hue: 190 },
  { id: "m3", kind: "video", name: "Drohnenflug.mp4", origin: "upload", duration: 24, hue: 140 },
  { id: "m4", kind: "image", name: "Titelbild Variante 2", origin: "ai", hue: 30 },
  { id: "m5", kind: "image", name: "Leuchtturm (Atelier)", origin: "legacy", hue: 280 },
  { id: "m6", kind: "audio", name: "Dialog Mira – Szene 1", origin: "ai", duration: 12, hue: 330 },
  { id: "m7", kind: "music", name: "Nordwind (Musik)", origin: "ai", duration: 60, hue: 260 },
  { id: "m8", kind: "element", name: "Mira (Figur)", origin: "ai", hue: 10 },
  { id: "m9", kind: "element", name: "Hafen (Ort)", origin: "ai", hue: 210 },
]

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
