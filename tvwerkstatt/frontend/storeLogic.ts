/** Reine Logik des Reiters Apps (ohne React), einzeln testbar. */
import type { TvwDesktop, TvwStoreApp } from "./api"

/** Suchtext wie der Server ihn annimmt: Buchstaben, Ziffern, Leerzeichen, . , & ' + -, 1–60 Zeichen. */
export function validQuery(q: string): boolean {
  const s = q.trim().replace(/\s+/g, " ")
  return s.length >= 1 && s.length <= 60 && /^[\p{L}\p{N}_ .,&'+-]+$/u.test(s)
}

/** Name zur App aus „Apps vom Fernseher lesen“ (Desktop), sonst der Paketname. */
export function nameOf(a: TvwStoreApp, desk: TvwDesktop | null): string {
  return desk?.apps.find((x) => x.package === a.package)?.label || a.package
}

/** Sortiert: Store-Apps zuerst, dann nach Name. */
export function sorted(apps: TvwStoreApp[], desk: TvwDesktop | null): TvwStoreApp[] {
  return [...apps].sort((a, b) => Number(b.store) - Number(a.store) || nameOf(a, desk).localeCompare(nameOf(b, desk)))
}

/** Herkunft als Text-Schlüssel. */
export function sourceKey(a: TvwStoreApp): string {
  return a.locked ? "apps.src_locked" : a.store ? "apps.src_store" : "apps.src_other"
}
