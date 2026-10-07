// Ghostwriter G2 – Gliederung aus Idee bearbeiten, bevor sie übernommen wird (outlineModel.test.ts).
// Alle Funktionen geben eine neue Gliederung zurück (React-Zustand bleibt unveränderlich).

export interface OutlineScene { title: string; summary: string; pov: string }
export interface OutlineChapter { title: string; scenes: OutlineScene[] }
export interface OutlineEntity { name: string; kind: "character" | "place" | "item"; description: string }
export interface Outline { chapters: OutlineChapter[]; entities: OutlineEntity[] }

const mapChapter = (o: Outline, ci: number, fn: (c: OutlineChapter) => OutlineChapter): Outline =>
  ({ ...o, chapters: o.chapters.map((c, i) => (i === ci ? fn(c) : c)) })

export function editScene(o: Outline, ci: number, si: number, patch: Partial<OutlineScene>): Outline {
  return mapChapter(o, ci, (c) => ({ ...c, scenes: c.scenes.map((s, i) => (i === si ? { ...s, ...patch } : s)) }))
}

export function renameChapter(o: Outline, ci: number, title: string): Outline {
  return mapChapter(o, ci, (c) => ({ ...c, title }))
}

export function removeChapter(o: Outline, ci: number): Outline {
  return { ...o, chapters: o.chapters.filter((_, i) => i !== ci) }
}

/** Szene streichen; war es die letzte des Kapitels, fällt das Kapitel weg (ein Kapitel ist nie leer). */
export function removeScene(o: Outline, ci: number, si: number): Outline {
  const next = mapChapter(o, ci, (c) => ({ ...c, scenes: c.scenes.filter((_, i) => i !== si) }))
  return next.chapters[ci]?.scenes.length ? next : removeChapter(next, ci)
}

export function outlineStats(o: Outline) {
  return { chapters: o.chapters.length, scenes: o.chapters.reduce((n, c) => n + c.scenes.length, 0) }
}

/** Grund, warum noch nicht übernommen werden kann – oder null. */
export function outlineProblem(o: Outline): "outline_empty" | "outline_title_missing" | "outline_summary_missing" | null {
  if (!o.chapters.length) return "outline_empty"
  for (const c of o.chapters) {
    if (!c.title.trim() || c.scenes.some((s) => !s.title.trim())) return "outline_title_missing"
    if (c.scenes.some((s) => !s.summary.trim())) return "outline_summary_missing"
  }
  return null
}
