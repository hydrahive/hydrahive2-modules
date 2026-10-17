/** Modelle fürs Drehbuch aus dem Modellkatalog des Kerns (wie im Atelier). Rein, ohne DOM – damit testbar. */
import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import type { MODEL_KEYS } from "./planApi"

export type ModelKind = (typeof MODEL_KEYS)[number]
export interface CatalogModel { id: string; name: string; local?: boolean; provider?: string }
export interface Catalog { default: string; models: CatalogModel[] }

/** Woher die Liste je Art kommt (Kern-Endpunkte, dieselben wie Atelier und Kern-Einstellungen). */
export const CATALOG_SOURCES: Record<ModelKind, string> = {
  video: "/llm/media-models?category=video",
  image: "/llm/media-models?category=image",
  music: "/llm/media-models?category=audio",
  voice: "/llm/models?modality=tts",
  text: "/llm/models?modality=chat",
}

/** Ab so vielen Einträgen gibt es ein Suchfeld. */
export const SEARCH_FROM = 25

/** Antwort von media-models (name) oder models (label) einheitlich machen; Unsinn → leer. */
export function toCatalog(raw: unknown): Catalog {
  const r = (raw && typeof raw === "object" ? raw : {}) as { default?: unknown; models?: unknown }
  const list = Array.isArray(r.models) ? r.models : []
  const models = list.flatMap((m) => {
    const x = (m && typeof m === "object" ? m : {}) as Record<string, unknown>
    if (typeof x.id !== "string" || !x.id) return []
    const name = typeof x.name === "string" && x.name ? x.name : typeof x.label === "string" && x.label ? x.label : x.id
    return [{ id: x.id, name, ...(x.local === true ? { local: true, provider: typeof x.provider === "string" ? x.provider : "" } : {}) }]
  })
  return { default: typeof r.default === "string" ? r.default : "", models }
}

export interface OptionGroup { group: string; models: { id: string; name: string }[] }

/** Gruppen für die Auswahl: gespeicherter Wert außerhalb der Liste („kept“), Cloud, lokal je Gerät. Suche nach ID/Name;
 *  der gewählte Wert bleibt immer sichtbar. */
export function modelOptions(cat: Catalog, value: string, query: string): OptionGroup[] {
  const q = query.trim().toLowerCase()
  const hit = (m: CatalogModel) => !q || m.id === value || m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q)
  const out: OptionGroup[] = []
  if (value && !cat.models.some((m) => m.id === value)) out.push({ group: "kept", models: [{ id: value, name: value }] })
  const cloud = cat.models.filter((m) => !m.local && hit(m)).sort((a, b) => Number(b.id === value) - Number(a.id === value))
  if (cloud.length) out.push({ group: "cloud", models: cloud.map(({ id, name }) => ({ id, name })) })
  const local = new Map<string, { id: string; name: string }[]>()
  for (const m of cat.models.filter((x) => x.local && hit(x))) local.set(m.provider || "", [...(local.get(m.provider || "") ?? []), { id: m.id, name: m.name }])
  for (const [device, models] of local) out.push({ group: `local:${device}`, models })
  return out
}

/** Lädt die Kataloge aller Arten einmal (null = lädt noch). Fehler → leerer Katalog (Freitext bleibt möglich). */
export function useModelCatalogs(active: boolean): Record<ModelKind, Catalog | null> {
  const [cats, setCats] = useState<Record<ModelKind, Catalog | null>>({ video: null, image: null, music: null, voice: null, text: null })
  useEffect(() => {
    if (!active) return
    let alive = true
    for (const kind of Object.keys(CATALOG_SOURCES) as ModelKind[]) {
      api.get<unknown>(CATALOG_SOURCES[kind]).then(toCatalog, () => toCatalog(null))
        .then((c) => { if (alive) setCats((x) => ({ ...x, [kind]: c })) })
    }
    return () => { alive = false }
  }, [active])
  return cats
}
