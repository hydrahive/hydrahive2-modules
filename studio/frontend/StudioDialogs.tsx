import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { HowTo } from "./HowTo"
import { SHORTCUTS, keyLabel, type ShortcutAction } from "./shortcuts"
import type { Workspace } from "./workspaces"

export function Backdrop({ onClose, children, label }: { onClose: () => void; children: React.ReactNode; label: string }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-[70] grid place-items-start justify-center bg-black/60 pt-[12vh]" role="dialog" aria-modal="true" aria-label={label}
      onPointerDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-[min(560px,92vw)] overflow-hidden rounded-[6px] border border-[#46617f] bg-[#0e1420] shadow-2xl">{children}</div>
    </div>
  )
}

/** Hilfe (Knopf „?“ bzw. Taste „?“): „So geht’s“ und alle Tastenkürzel. */
export function ShortcutHelp({ onClose, onGo }: { onClose: () => void; onGo?: (w: Workspace) => void }) {
  const { t } = useTranslation("studio")
  const [tab, setTab] = useState<"howto" | "keys">("howto")
  return (
    <Backdrop onClose={onClose} label={t("howto_title")}>
      <div className="flex gap-1 border-b border-[#2a364b] px-3 pt-2" role="tablist">
        {(["howto", "keys"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-t-[4px] px-3 py-1.5 text-xs font-black ${tab === k ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#8d9ab0] hover:text-[#e8eef8]"}`}>
            {k === "howto" ? t("howto_title") : t("howto_tab_shortcuts")}
          </button>
        ))}
      </div>
      {tab === "howto" ? <HowTo onGo={(w) => { onClose(); onGo?.(w) }} /> : (
      <ul className="max-h-[60vh] divide-y divide-[#1e2738] overflow-y-auto px-4 py-1 text-xs" data-studio-help>
        {SHORTCUTS.map((s) => (
          <li key={s.action} className="flex items-center justify-between gap-3 py-1.5">
            <span className="text-[#c3ccdd]">{t(`action.${s.action}`)}</span>
            <span className="flex gap-1">{s.keys.map((k) => <kbd key={k} className="rounded border border-[#2a364b] bg-[#111827] px-1.5 py-0.5 font-mono text-[10px] text-[#e8eef8]">{keyLabel(k)}</kbd>)}</span>
          </li>
        ))}
      </ul>
      )}
    </Backdrop>
  )
}

/** Befehlssuche (Strg+K): alle Aktionen per Suche auslösen. */
export function CommandPalette({ onClose, onRun }: { onClose: () => void; onRun: (a: ShortcutAction) => void }) {
  const { t } = useTranslation("studio")
  const [q, setQ] = useState("")
  const [idx, setIdx] = useState(0)
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  const hits = useMemo(() => SHORTCUTS.filter((s) => s.action !== "command"
    && t(`action.${s.action}`).toLowerCase().includes(q.trim().toLowerCase())), [q, t])
  const run = (a: ShortcutAction) => { onClose(); onRun(a) }
  return (
    <Backdrop onClose={onClose} label={t("command_title")}>
      <input ref={ref} value={q} placeholder={t("command_placeholder")} data-studio-command-input
        onChange={(e) => { setQ(e.target.value); setIdx(0) }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, hits.length - 1)) }
          if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)) }
          if (e.key === "Enter" && hits[idx]) run(hits[idx].action)
        }}
        className="w-full border-b border-[#2a364b] bg-transparent px-4 py-3 text-sm text-[#e8eef8] outline-none placeholder:text-[#68758a]" />
      <ul className="max-h-[50vh] overflow-y-auto py-1 text-xs">
        {hits.map((s, i) => (
          <li key={s.action}>
            <button type="button" onClick={() => run(s.action)} onPointerEnter={() => setIdx(i)}
              className={`flex w-full items-center justify-between px-4 py-1.5 text-left ${i === idx ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#c3ccdd]"}`}>
              <span>{t(`action.${s.action}`)}</span>
              <kbd className="font-mono text-[10px] text-[#68758a]">{keyLabel(s.keys[0])}</kbd>
            </button>
          </li>
        ))}
        {!hits.length && <li className="px-4 py-2 text-[#68758a]">{t("command_none")}</li>}
      </ul>
    </Backdrop>
  )
}
