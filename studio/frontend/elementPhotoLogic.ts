/** Figur/Ort aus Foto (C2): reine Hilfen + API. Backend: backend/cast.py, describe.py, element_routes.py. */
import { api } from "@/shared/api-client"
import type { ElementKind, PlanElement } from "./planApi"

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/plan/elements`

export const describeApi = {
  describe: (pid: string, id: string) => api.post<PlanElement>(`${base(pid)}/${encodeURIComponent(id)}/describe`, {}),
  fromImage: (pid: string, d: { rel: string; kind: ElementKind; name: string }) => api.post<PlanElement>(`${base(pid)}/from-image`, d),
}

/** Wer ist im Bild (Server: `cast` je Shot) – mit Namen und ob ein Vorlage-Foto mitgeht. Gelöschte fallen weg. */
export function castNames(cast: string[] | undefined, elements: PlanElement[]): { id: string; name: string; photo: boolean }[] {
  const by = new Map(elements.map((e) => [e.id, e]))
  return (cast ?? []).flatMap((id) => {
    const e = by.get(id)
    return e ? [{ id, name: e.name, photo: e.references.length > 0 }] : []
  })
}

/** Nach dem ersten Foto automatisch beschreiben – nur, wenn noch nichts eingetragen ist (nie überschreiben). */
export function needsDescription(e: PlanElement): boolean {
  return e.references.length > 0 && !e.description.trim() && !e.style_anchor.trim()
}
