import { useEffect, useState } from "react"
import { llmModelsApi, type RegistryModel } from "@/features/llm/api"

export interface ModelCatalog { standard: string; selected: string; ids: string[]; models: RegistryModel[] }

/** Chat-Modelle einmal laden (dieselbe Liste wie im Agent-Editor). Fehler → null, das Formular blockiert dann nicht. */
export function useModelCatalog(): ModelCatalog | null {
  const [cat, setCat] = useState<ModelCatalog | null>(null)
  useEffect(() => {
    let alive = true
    llmModelsApi.byModality("chat")
      .then((r) => { if (alive) setCat({ standard: r.default, selected: r.selected || "", ids: r.models.map((m) => m.id), models: r.models }) })
      .catch(() => {})
    return () => { alive = false }
  }, [])
  return cat
}
