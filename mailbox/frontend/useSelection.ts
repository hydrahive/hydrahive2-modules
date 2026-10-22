import { useCallback, useState } from "react"
import { mailApi, type MailAction, type MailItem } from "./api"
import { needsConfirm } from "./composeFormat"
import { toggle, toggleAll } from "./listLogic"

const EMPTY: Set<number> = new Set()

/** Mehrfachauswahl der Liste + Sammel-Aktion. Wechsel von Ordner/Suche leert die Auswahl (keine unsichtbaren Treffer). */
export function useSelection(items: MailItem[], resetKey: string, onDone: (msg: string | null) => void,
                             texts: { done: (n: number) => string; skipped: (n: number) => string; failed: string; confirmDelete: (n: number) => string }) {
  // Auswahl gehört zu Ordner/Suche: bei anderem resetKey ist sie leer (abgeleitet statt im Effekt zurückgesetzt)
  const [state, setState] = useState<{ key: string; ids: Set<number> }>({ key: resetKey, ids: new Set() })
  const checked = state.key === resetKey ? state.ids : EMPTY
  const setChecked = useCallback((f: Set<number> | ((s: Set<number>) => Set<number>)) => setState((st) => {
    const cur = st.key === resetKey ? st.ids : EMPTY
    return { key: resetKey, ids: typeof f === "function" ? f(cur) : f }
  }), [resetKey])
  const [busy, setBusy] = useState(false)

  const check = useCallback((id: number) => setChecked((s) => toggle(s, id)), [setChecked])
  const checkAll = useCallback(() => setChecked((s) => toggleAll(s, items.map((m) => m.id))), [items, setChecked])

  const act = useCallback(async (action: MailAction) => {
    if (needsConfirm(action) && !window.confirm(texts.confirmDelete(checked.size))) return
    setBusy(true)
    try {
      const r = await mailApi.act([...checked], action)
      onDone([r.done ? texts.done(r.done) : "", r.skipped ? texts.skipped(r.skipped) : ""].filter(Boolean).join(" · ") || null)
      setChecked(new Set())
    } catch {
      onDone(texts.failed)
    } finally {
      setBusy(false)
    }
  }, [checked, onDone, texts, setChecked])

  return { checked, busy, check, checkAll, act, clear: () => setChecked(new Set()) }
}
