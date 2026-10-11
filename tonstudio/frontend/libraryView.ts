import type { LibraryItem } from "./types"

export type Sort = "new" | "name" | "length"
export const GROUPS: LibraryItem["group"][] = ["tonstudio", "atelier", "generated", "media"]

/** Bibliothek gliedern (feste Gruppen-Reihenfolge), filtern (Name, Prompt, Modell) und sortieren. Leere Gruppen fallen weg. */
export function groupLibrary(items: LibraryItem[], sort: Sort, query: string): { g: LibraryItem["group"]; list: LibraryItem[] }[] {
  const q = query.trim().toLowerCase()
  const hit = (i: LibraryItem) => !q || [i.name, i.prompt ?? "", i.model ?? "", i.source_rel].some((s) => s.toLowerCase().includes(q))
  const cmp = (a: LibraryItem, b: LibraryItem) =>
    sort === "name" ? a.name.localeCompare(b.name, "de", { sensitivity: "base" })
      : sort === "length" ? (b.duration ?? 0) - (a.duration ?? 0)
        : (b.created_at ?? "").localeCompare(a.created_at ?? "")
  return GROUPS.map((g) => ({ g, list: items.filter((i) => i.group === g && hit(i)).sort(cmp) })).filter((x) => x.list.length > 0)
}

/** Anzeigename: bekannter Name, sonst „Song vom TT.MM.JJJJ, HH:MM“ statt UUID-Dateiname. */
export function displayName(i: LibraryItem, fallback: (date: string) => string): string {
  if (i.named !== false) return i.name
  if (!i.created_at) return i.name
  const d = new Date(i.created_at)
  if (Number.isNaN(d.getTime())) return i.name
  const p = (n: number) => String(n).padStart(2, "0")
  return fallback(`${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}, ${p(d.getHours())}:${p(d.getMinutes())}`)
}
