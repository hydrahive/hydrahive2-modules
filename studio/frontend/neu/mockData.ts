/** ATTRAPPE „Geführtes Studio“ (19.10.): Beispieldaten. Nichts hiervon geht an den Server. */
import abschied from "./bilder/abschied.jpg"
import drache from "./bilder/drache.jpg"
import halloween from "./bilder/halloween.jpg"
import herbst from "./bilder/herbst.jpg"
import hydraFoto from "./bilder/hydra-foto.jpg"
import probe1 from "./bilder/probe-1.jpg"
import probe2 from "./bilder/probe-2.jpg"
import weihnachten from "./bilder/weihnachten.jpg"
import winter from "./bilder/winter.jpg"

export const PICS = { hydraFoto, probe1, probe2, drache }

export type FilmKind = "trailer" | "erklaer" | "kurz" | "musik"
export type FilmFormat = "quer" | "hoch"

export interface Scene {
  id: string
  text: string
  /** Bilder dieser Szene; `pick` ist das gewählte */
  images: string[]
  pick: number
  /** das Bild, das die „KI“ in der Attrappe liefert */
  sample: string
  imageBusy: boolean
  clip: "none" | "busy" | "done" | "still"
  cast: string[]
}

export interface Person {
  id: string
  kind: "figur" | "ort"
  name: string
  photo?: string
  probe?: string
  state: "leer" | "busy" | "probe" | "passt" | "ohne"
}

export const KINDS: { id: FilmKind; label: string }[] = [
  { id: "trailer", label: "Trailer" }, { id: "erklaer", label: "Erklärfilm" },
  { id: "kurz", label: "Kurzfilm" }, { id: "musik", label: "Musikvideo" },
]
export const LENGTHS = ["30 Sekunden", "1 Minute", "2 Minuten"]
export const EXAMPLE_IDEA = "Ein Trailer über Hydra, ein freundliches Wesen mit fünf Köpfen, das ein ganzes Jahr erlebt: Herbst, Halloween, Schnee und Weihnachten. Am Ende stellt sich Hydra vor."

const STORY: [string, string, string[]][] = [
  ["Hydra wacht im Herbstwald auf. Goldene Blätter fallen auf die fünf Köpfe.", herbst, ["hydra", "wald"]],
  ["An Halloween trägt Hydra Kürbisse auf den Köpfen und erschreckt die Fledermäuse.", halloween, ["hydra"]],
  ["Der erste Schnee: Hydra staunt über die weiße Landschaft.", winter, ["hydra"]],
  ["Weihnachten vor dem Haus – jeder Kopf trägt eine Mütze.", weihnachten, ["hydra"]],
  ["Zum Schluss winkt Hydra in die Kamera: „Willkommen – ich bin Hydra!“", abschied, ["hydra"]],
]

export const storyScenes = (): Scene[] => STORY.map(([text, sample, cast], i) => ({
  id: `s${i + 1}`, text, images: [], pick: 0, sample, imageBusy: false, clip: "none", cast,
}))

export const emptyScene = (n: number): Scene => ({
  id: `s${Date.now()}`, text: "", images: [], pick: 0, sample: [herbst, winter, halloween][n % 3], imageBusy: false, clip: "none", cast: [],
})

export const suggestedCast = (): Person[] => [
  { id: "hydra", kind: "figur", name: "Hydra", state: "leer" },
  { id: "wald", kind: "ort", name: "Herbstwald", state: "leer" },
]

/** Richtwerte wie im echten Studio (Bild ≈ 1,5 ct, Musik ≈ 4 ct). Clip und Stimme: Beispielwerte der Attrappe. */
export const COST = { image: 1.5, clip: 30, music: 4, voice: 1 }
export const ct = (v: number) => `≈ ${v.toLocaleString("de-DE", { maximumFractionDigits: 1 })} Cent`

/** Wartezeit der Attrappe statt echter Erzeugung */
export const fake = (ms = 1400) => new Promise<void>((r) => setTimeout(r, ms))

/** Zoom-Bewegung als Platzhalter für einen echten Clip */
export const MOTION_CSS = "@keyframes hhGuidedKen{0%{transform:scale(1) translate(0,0)}100%{transform:scale(1.12) translate(-2%,-1%)}}"
export const motion = { animation: "hhGuidedKen 5s ease-in-out infinite alternate" }
