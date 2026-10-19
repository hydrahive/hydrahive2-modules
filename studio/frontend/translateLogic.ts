import { api } from "@/shared/api-client"
import { LANGUAGES, type Job } from "./planApi"

/** Übersetzen und Sprachen der Untertitel (Spec „Bauplan 6c“). Rein, damit testbar. */
export interface LanguageEntry { language: string; count: number }
export interface LanguageList { film: string; languages: LanguageEntry[] }

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/subtitles`
export const translateApi = {
  languages: (pid: string) => api.get<LanguageList>(base(pid)),
  start: (pid: string, to: string, from: string, replace: boolean) =>
    api.post<Job>(`${base(pid)}/${encodeURIComponent(to)}/translate`, { from, ...(replace ? { replace: true } : {}) }),
}

/** Auswahl im Reiter: Filmsprache zuerst, dann vorhandene; die gewählte bleibt sichtbar, auch wenn sie (noch) leer ist. */
export function languageChoices(list: LanguageList | null, value: string): (LanguageEntry & { film: boolean })[] {
  const film = list?.film ?? value
  const known = list?.languages ?? [{ language: film, count: 0 }]
  const all = known.some((x) => x.language === value) || !value ? known : [...known, { language: value, count: 0 }]
  return all.map((x) => ({ ...x, film: x.language === film }))
}

/** Zielsprachen: alle bekannten außer der Ausgangssprache, mit Anzahl vorhandener Untertitel. */
export function targetChoices(list: LanguageList | null, from: string): LanguageEntry[] {
  const have = new Map((list?.languages ?? []).map((x) => [x.language, x.count]))
  return LANGUAGES.filter((l) => l !== from).map((l) => ({ language: l, count: have.get(l) ?? 0 }))
}

export function finishedTranslate(jobs: Job[], pending: Set<string>): Job | null {
  return jobs.find((j) => j.kind === "translate" && pending.has(j.id) && (j.status === "done" || j.status === "failed" || j.status === "cancelled")) ?? null
}
