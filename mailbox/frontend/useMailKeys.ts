import { useEffect, useRef } from "react"
import type { MailDetail, MailItem } from "./api"
import { keyAction, nextId, type KeyAction } from "./listLogic"

interface Handlers {
  items: MailItem[]
  open: MailDetail | null
  composing: boolean
  select: (id: number) => void
  compose: () => void
  reply: (mode: "reply" | "reply_all" | "forward") => void
  act: (action: "archive" | "delete") => void
  focusSearch: () => void
}

/** Tastenkürzel (Spec §6): j/k r a f e # / c. Aus, solange das Schreibfenster offen ist oder in Feldern getippt wird. */
export function useMailKeys(h: Handlers) {
  const ref = useRef(h)
  useEffect(() => { ref.current = h })            // nach jedem Rendern aktualisieren, nicht während des Renderns
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const a: KeyAction | null = keyAction({ key: e.key, ctrlKey: e.ctrlKey, metaKey: e.metaKey, altKey: e.altKey,
        target: e.target as HTMLElement | null })
      const c = ref.current
      if (!a || c.composing) return
      const ids = c.items.map((m) => m.id)
      const cur = c.open?.id ?? null
      const run: Record<KeyAction, () => void> = {
        next: () => { const n = nextId(ids, cur, 1); if (n != null) c.select(n) },
        prev: () => { const n = nextId(ids, cur, -1); if (n != null) c.select(n) },
        reply: () => { if (c.open) c.reply("reply") },
        reply_all: () => { if (c.open) c.reply("reply_all") },
        forward: () => { if (c.open) c.reply("forward") },
        archive: () => { if (c.open) c.act("archive") },
        delete: () => { if (c.open) c.act("delete") },
        search: () => c.focusSearch(),
        compose: () => c.compose(),
      }
      e.preventDefault()
      run[a]()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])
}

/** Browser-Benachrichtigung (Spec §6), nur nach ausdrücklichem Einschalten (localStorage + Browser-Erlaubnis).
 *  Meldet nur einen Anstieg der ungelesenen Posteingangs-Mails, ohne Inhalt (kein Absender, kein Betreff). */
export function useNewMailNotice(unread: number, text: (n: number) => { title: string; body: string }) {
  const last = useRef<number | null>(null)
  useEffect(() => {
    const prev = last.current
    last.current = unread
    if (prev == null || unread <= prev) return
    if (localStorage.getItem("mailbox.notify") !== "1") return
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return
    const m = text(unread - prev)
    new Notification(m.title, { body: m.body, tag: "mailbox-new" })
  }, [unread, text])
}
