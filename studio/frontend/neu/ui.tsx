/** Geführter Weg: gemeinsame Bausteine (großer Knopf, kleiner Knopf, Kopf eines Schritts, Hinweis). */
import type { ReactNode } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"

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
  const { t } = useTranslation("studio")
  return (
    <header className="mb-5">
      <div className="text-xs font-black uppercase tracking-[0.2em] text-[#3ddc97]">{t("guided.step_of", { n })}</div>
      <h1 className="mt-1 text-3xl font-black text-[#f2f6fc]">{title}</h1>
      <p className="mt-2 max-w-2xl text-base leading-relaxed text-[#b4bfd2]">{text}</p>
    </header>
  )
}

export function Notice({ children }: { children: ReactNode }) {
  return <div className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{children}</div>
}
