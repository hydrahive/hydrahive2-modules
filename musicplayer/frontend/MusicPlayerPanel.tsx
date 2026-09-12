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
    <section className="w-full min-w-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b] text-[#e8eef8]">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={!collapsed}
        className="flex w-full items-center gap-3 p-3 text-left transition-colors hover:bg-[#172133] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[#69d7ff]"
      >
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-[4px] border border-[#2a364b] bg-[#0d1420] text-fuchsia-300">
          <Music size={15} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="mb-1 block text-[9px] font-black uppercase tracking-[0.16em] text-[#69d7ff]">MEDIA</span>
          <span className="block truncate text-sm font-bold text-[#e8eef8]">{title}</span>
        </span>
        <span className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1 text-[10px] font-bold tabular-nums text-[#8d9ab0]">
          {trackCount}
        </span>
        {collapsed
          ? <ChevronRight size={14} className="shrink-0 text-[#8d9ab0]" />
          : <ChevronDown size={14} className="shrink-0 text-[#69d7ff]" />}
      </button>
      {!collapsed && <div className="border-t border-[#2a364b] p-3">{children}</div>}
    </section>
  )
}
