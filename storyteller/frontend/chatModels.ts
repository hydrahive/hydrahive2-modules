// Chat-Modelle für das Auswahlfeld: einmal je Seitenaufruf laden (Liste ist groß, ändert sich selten).
import { llmModelsApi, type RegistryModel } from "@/features/llm/api"

export interface Catalog { models: RegistryModel[]; standard: string }
let cache: Promise<Catalog> | null = null

export function loadChatModels(): Promise<Catalog> {
  cache ??= llmModelsApi.byModality("chat")
    .then((r) => ({ models: r.models, standard: r.selected || r.default }))
    .catch((e: unknown) => { cache = null; throw e })
  return cache
}
