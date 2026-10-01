export type SaveState = "saved" | "saving" | "error" | "too_large"

type RequestError = { status?: unknown; message?: unknown }

export function beginSave(): SaveState {
  return "saving"
}

export function saveStateForError(error: unknown): SaveState {
  const { status, message } = (error ?? {}) as RequestError
  // PUT returns 400/scratchpad_too_large for the byte limit. Pydantic returns
  // 422 first when the character limit is exceeded.
  if ((status === 400 && message === "scratchpad_too_large") || status === 422) return "too_large"
  return "error"
}

export function persistUserText(save: (content: string) => Promise<unknown>, content: string): Promise<SaveState> {
  return save(content)
    .then(() => "saved" as const)
    .catch((error: unknown) => saveStateForError(error))
}
