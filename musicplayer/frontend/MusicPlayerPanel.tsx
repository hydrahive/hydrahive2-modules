import { ChevronDown, ChevronRight, Music } from "lucide-react"
import { type ReactNode, useState } from "react"

const STORAGE_KEY = "hh2.box.buddy-musicplayer"

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1"
  } catch {
    return false
  }
}

interface Props {
  title: string
  trackCount: number
  children: ReactNode
}

/** Modul-lokale Hülle im flachen Design des neuen Buddy-Cockpits. */
export function MusicPlayerPanel({ title, trackCount, children }: Props) {
  const [collapsed, setCollapsed] = useState(readCollapsed)

  const toggle = () => {
    setCollapsed((current) => {
      const next = !current
      try {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0")
      } catch {
        // Persistenz ist optional; Bedienung funktioniert auch ohne Storage.
      }
      return next
    })
  }

  return (
    <section className="w-full min-w-0 overflow-hidden rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] text-[#e8eef8]">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={!collapsed}
        className="flex w-full items-center gap-3 p-3 text-left transition-colors hover:bg-[rgb(var(--hh-s-hebung,23_33_51))] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[#69d7ff]"
      >
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] text-fuchsia-300">
          <Music size={15} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="mb-1 block text-[9px] font-black uppercase tracking-[0.16em] text-[#69d7ff]">MEDIA</span>
          <span className="block truncate text-sm font-bold text-[#e8eef8]">{title}</span>
        </span>
        <span className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-[10px] font-bold tabular-nums text-[#9aa7bc]">
          {trackCount}
        </span>
        {collapsed
          ? <ChevronRight size={14} className="shrink-0 text-[#9aa7bc]" />
          : <ChevronDown size={14} className="shrink-0 text-[#69d7ff]" />}
      </button>
      {!collapsed && <div className="border-t border-[rgb(var(--hh-s-rand,42_54_75))] p-3">{children}</div>}
    </section>
  )
}
