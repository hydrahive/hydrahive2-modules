import { Copy, History, MessagesSquare } from "lucide-react"
import { BUTTON, BUTTON_ON } from "./styles"
import type { T } from "./texts.de"

interface Props {
  versionsOpen: boolean
  chatOpen: boolean
  copied: "" | "ok" | "fail"
  t: T
  onVersions: () => void
  onChat: () => void
  onCopy: () => void
}

/** Knöpfe rechts in der Kopfzeile des Editors: frühere Fassungen, Chat mit dem Agenten, Board als Text kopieren. */
export function EditorActions({ versionsOpen, chatOpen, copied, t, onVersions, onChat, onCopy }: Props) {
  return (
    <>
      <button type="button" onClick={onVersions} aria-pressed={versionsOpen} className={versionsOpen ? BUTTON_ON : BUTTON}>
        <History size={13} aria-hidden />{t("versions_title")}
      </button>
      <button type="button" onClick={onChat} aria-pressed={chatOpen} title={t("chat_title")}
        className={chatOpen ? BUTTON_ON : BUTTON}>
        <MessagesSquare size={13} aria-hidden />{t("chat_open")}
      </button>
      <button type="button" onClick={onCopy} title={t("copy_hint")} className={BUTTON}>
        <Copy size={13} aria-hidden />
        {copied === "ok" ? t("copied") : copied === "fail" ? t("copy_failed") : t("copy")}
      </button>
    </>
  )
}
