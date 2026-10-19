/** Anordnung der Statuszentrale (S4) – gleiche Prüfung wie renderer/dash_layout.py (Server und Dienst). */
export const AREAS = ["messages", "home", "hydra", "tasks", "github", "machine", "mining"] as const
export type AreaId = (typeof AREAS)[number]

export interface DashboardCfg {
  tasks_user: string
  github_project: string
  github_repos: string[]
  order: AreaId[]
  hidden: AreaId[]
  messages_max: number
  home_rooms: string[]
  mining_in_machine: boolean
  /** S5: Bereich → Seite 1–3. */
  pages: Record<AreaId, number>
  /** S6: Chat-Seite am Gehäuse. */
  chat_enabled: boolean
}

export const DEFAULT_PAGES: Record<AreaId, number> = { messages: 1, home: 1, hydra: 1, tasks: 2, github: 2, machine: 2, mining: 2 }

export const DEFAULT_DASHBOARD: DashboardCfg = {
  tasks_user: "till", github_project: "Hydrahive DEV",
  github_repos: ["hydrahive/hydrahive2.0", "hydrahive/hydrahive2-modules"],
  order: [...AREAS], hidden: [], messages_max: 3, home_rooms: [], mining_in_machine: true, pages: { ...DEFAULT_PAGES },
  chat_enabled: true,
}

const USER_RE = /^[A-Za-z0-9_.@-]{1,64}$/
const REPO_RE = /^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/
/** Wie dash_layout._ROOM: 1–60 Zeichen, keine < > & " und keine Steuerzeichen. */
const roomOk = (r: string): boolean =>
  r.length >= 1 && r.length <= 60 && ![...r].some((c) => "<>&\"".includes(c) || c.charCodeAt(0) < 32)
const isArea = (x: string): x is AreaId => (AREAS as readonly string[]).includes(x)

/** Gespeicherte (evtl. alte S2-)Einstellung → vollständig; fehlende Bereiche hinten angehängt. */
export function normalizeDashboard(d: Partial<DashboardCfg> | undefined): DashboardCfg {
  const out: DashboardCfg = { ...DEFAULT_DASHBOARD, ...(d ?? {}) }
  const order = (out.order ?? []).filter(isArea)
  out.order = [...order, ...AREAS.filter((a) => !order.includes(a))]
  out.hidden = (out.hidden ?? []).filter(isArea)
  out.pages = { ...DEFAULT_PAGES, ...(d?.pages ?? {}) }
  return out
}

/** Fehlerschlüssel für die Anzeige; leer = gültig. */
export function layoutErrors(d: DashboardCfg): string[] {
  const errs: string[] = []
  if (!USER_RE.test(d.tasks_user)) errs.push("tasks_user")
  if (!d.github_project.trim() || d.github_project.length > 100) errs.push("github_project")
  if (d.github_repos.length > 5 || d.github_repos.some((r) => !REPO_RE.test(r) || r.split("/").some((p) => p === "." || p === "..")))
    errs.push("github_repos")
  if (new Set(d.order).size !== d.order.length || !d.order.every(isArea) || !d.hidden.every(isArea)) errs.push("order")
  if (!Number.isInteger(d.messages_max) || d.messages_max < 1 || d.messages_max > 5) errs.push("messages_max")
  if (d.home_rooms.length > 20 || d.home_rooms.some((r) => !roomOk(r))) errs.push("home_rooms")
  if (Object.entries(d.pages).some(([k, v]) => !isArea(k) || !Number.isInteger(v) || v < 1 || v > 3)) errs.push("pages")
  return errs
}

export function moveArea(order: AreaId[], id: AreaId, step: -1 | 1): AreaId[] {
  const i = order.indexOf(id), j = i + step
  if (i < 0 || j < 0 || j >= order.length) return order
  const next = [...order]
  ;[next[i], next[j]] = [next[j], next[i]]
  return next
}

/** Anzeige-Reihenfolge im Cockpit: nach Seite, innerhalb der Seite wie `order`. */
export function byPage(d: DashboardCfg): AreaId[] {
  return [...d.order].sort((a, b) => (d.pages[a] ?? 1) - (d.pages[b] ?? 1))
}

/** ↑/↓ innerhalb der eigenen Seite (so wie angezeigt). Am Seitenanfang/-ende passiert nichts. */
export function moveInPage(d: DashboardCfg, id: AreaId, step: -1 | 1): AreaId[] {
  const page = d.pages[id] ?? 1
  const same = d.order.filter((x) => (d.pages[x] ?? 1) === page)
  const j = same.indexOf(id) + step
  if (j < 0 || j >= same.length) return d.order
  return swap(d.order, id, same[j])
}

function swap(order: AreaId[], a: AreaId, b: AreaId): AreaId[] {
  const next = [...order], i = next.indexOf(a), j = next.indexOf(b)
  ;[next[i], next[j]] = [next[j], next[i]]
  return next
}

export function toggleIn<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item]
}

export const parseRepos = (s: string): string[] => s.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean)
