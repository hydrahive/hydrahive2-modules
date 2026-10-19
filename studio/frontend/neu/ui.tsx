/** ATTRAPPE „Geführtes Studio“: gemeinsame Bausteine (großer Knopf, Gesichter, Kopf eines Schritts). */
import type { ReactNode } from "react"
import { Loader2 } from "lucide-react"
import type { Person } from "./mockData"

export function BigButton({ children, onClick, busy, disabled, tone = "main", cost }: {
  children: ReactNode; onClick: () => void; busy?: boolean; disabled?: boolean; tone?: "main" | "plain" | "danger"; cost?: string
}) {
  const look = tone === "main" ? "bg-[#3ddc97] text-[#04140d] hover:bg-[#5ee6aa]"
    : tone === "danger" ? "border border-[#ff7a7a]/60 text-[#ff9b9b] hover:bg-[#ff7a7a]/10"
    : "border border-[#46617f] text-[#e8eef8] hover:bg-[#1c2940]"
  return (
    <button type="button" onClick={onClick} disabled={busy || disabled}
      className={`inline-flex items-center gap-2 rounded-[8px] px-4 py-2.5 text-sm font-bold disabled:opacity-50 ${look}`}>
      {busy && <Loader2 size={16} className="animate-spin" />}
      {children}
      {cost && <span className="rounded-full bg-black/20 px-2 py-0.5 text-xs font-semibold">{cost}</span>}
    </button>
  )
}

export function SmallButton({ children, onClick, disabled, label }: { children: ReactNode; onClick: () => void; disabled?: boolean; label?: string }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label}
      className="inline-flex items-center gap-1 rounded-[6px] border border-[#2a364b] px-2.5 py-1.5 text-xs font-semibold text-[#c3ccdd] hover:bg-[#1c2940] disabled:opacity-40">
      {children}
    </button>
  )
}

export function StepHead({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <header className="mb-5">
      <div className="text-xs font-black uppercase tracking-[0.2em] text-[#3ddc97]">Schritt {n} von 5</div>
      <h1 className="mt-1 text-3xl font-black text-[#f2f6fc]">{title}</h1>
      <p className="mt-2 max-w-2xl text-base leading-relaxed text-[#b4bfd2]">{text}</p>
    </header>
  )
}

export function Face({ p, size = 28 }: { p: Person; size?: number }) {
  const pic = p.state === "passt" || p.state === "probe" ? p.probe : p.photo
  return pic
    ? <img src={pic} alt={p.name} title={p.name} style={{ width: size, height: size }} className="rounded-full border-2 border-[#0b111b] object-cover" />
    : <span title={p.name || "?"} style={{ width: size, height: size }}
        className="grid place-items-center rounded-full border-2 border-[#0b111b] bg-[#2a364b] text-[11px] font-black text-[#e8eef8]">
        {(p.name || "?").slice(0, 1).toUpperCase()}
      </span>
}

/** „Mit dabei“: wer in dieser Szene vorkommt – anklickbar an/aus */
export function CastChips({ people, cast, onToggle }: { people: Person[]; cast: string[]; onToggle?: (id: string) => void }) {
  if (!people.length) return null
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-[#8d9ab0]">Mit dabei:</span>
      {people.map((p) => {
        const on = cast.includes(p.id)
        return (
          <button key={p.id} type="button" onClick={() => onToggle?.(p.id)} aria-pressed={on} disabled={!onToggle}
            className={`flex items-center gap-1 rounded-full py-0.5 pl-0.5 pr-2 text-xs font-semibold ${on ? "bg-[#3ddc97]/15 text-[#c9f7e2]" : "bg-transparent text-[#5f6d84] line-through"}`}>
            <Face p={p} size={20} /> {p.name || "ohne Namen"}
          </button>
        )
      })}
    </div>
  )
}

export function Notice({ children }: { children: ReactNode }) {
  return <div className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{children}</div>
}
