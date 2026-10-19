/** Lokale Modelle (eigener Rechner: ComfyUI `local:…`, Ollama `ollama/…`) kosten nichts – Bauplan L. */
export function isLocalModel(model?: string): boolean {
  return !!model && (model.startsWith("local:") || model.startsWith("ollama/"))
}
