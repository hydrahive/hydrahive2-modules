/** Panel-Aufteilung des Studios: ziehbar, je Browser gespeichert (Spec „Grundsätze“ 1). */

export interface StudioLayout {
  /** Breite der Bibliothek in % der Fensterbreite. */
  library: number
  /** Breite der Eigenschaften in %. */
  inspector: number
  /** Höhe der Zeitleiste in % der Arbeitsfläche. */
  timeline: number
}

export const DEFAULT_LAYOUT: StudioLayout = { library: 20, inspector: 22, timeline: 40 }

const LIMITS: Record<keyof StudioLayout, [number, number]> = {
  library: [12, 35],
  inspector: [14, 35],
  timeline: [20, 70],
}

export const STORAGE_KEY = "hh.studio.layout.v1"

export function clampLayout(raw: Partial<Record<keyof StudioLayout, unknown>> | null | undefined): StudioLayout {
  const out = { ...DEFAULT_LAYOUT }
  for (const key of Object.keys(LIMITS) as (keyof StudioLayout)[]) {
    const v = raw?.[key]
    if (typeof v === "number" && Number.isFinite(v)) {
      const [lo, hi] = LIMITS[key]
      out[key] = Math.min(hi, Math.max(lo, v))
    }
  }
  return out
}

export function loadLayout(storage: Pick<Storage, "getItem"> | undefined = globalThis.localStorage): StudioLayout {
  try {
    return clampLayout(JSON.parse(storage?.getItem(STORAGE_KEY) ?? "null"))
  } catch {
    return { ...DEFAULT_LAYOUT }
  }
}

export function saveLayout(layout: StudioLayout, storage: Pick<Storage, "setItem"> | undefined = globalThis.localStorage) {
  try {
    storage?.setItem(STORAGE_KEY, JSON.stringify(clampLayout(layout)))
  } catch {
    /* privater Modus o. Ä. – dann eben nicht merken */
  }
}

/** Neue Größe nach einem Zug am Trenner: `delta` in % (positiv = nach rechts/unten). */
export function dragLayout(layout: StudioLayout, key: keyof StudioLayout, delta: number): StudioLayout {
  const sign = key === "library" ? 1 : -1          // Bibliothek wächst nach rechts, Eigenschaften/Zeitleiste wachsen nach links/oben
  return clampLayout({ ...layout, [key]: layout[key] + sign * delta })
}
