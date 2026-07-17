import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react"
import { AlertTriangle, Inbox, LoaderCircle, RefreshCw } from "lucide-react"

export const panel = "rounded-[6px] border border-[#2a364b] bg-[#101724]"
export const input = "w-full rounded-[4px] border border-[#33425a] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none placeholder:text-[#59677d] focus:border-[#69d7ff]"

export function Button({ tone = "default", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "default" | "primary" | "danger" }) {
  const tones = { default: "border-[#33425a] bg-[#172133] text-[#d4deeb] hover:border-[#5b7190]", primary: "border-cyan-400/40 bg-cyan-400/15 text-cyan-200 hover:bg-cyan-400/25", danger: "border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20" }
  return <button {...props} className={`rounded-[4px] border px-3 py-2 text-xs font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${tones[tone]} ${className}`} />
}
export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="grid gap-1 text-xs font-semibold text-[#b5c1d2]"><span>{label}</span>{children}{hint && <span className="font-normal text-[#718097]">{hint}</span>}</label>
}
export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input {...props} className={`${input} ${props.className ?? ""}`} /> }
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select {...props} className={`${input} ${props.className ?? ""}`} /> }
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea {...props} className={`${input} ${props.className ?? ""}`} /> }
export function LoadingState({ label = "Daten werden geladen …" }: { label?: string }) { return <div className={`${panel} grid min-h-40 place-items-center p-8 text-sm text-[#8d9ab0]`}><span className="flex items-center gap-2"><LoaderCircle className="animate-spin" size={18} />{label}</span></div> }
export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) { return <div className={`${panel} grid min-h-40 place-items-center p-8 text-center`}><div><Inbox className="mx-auto mb-3 text-[#718097]" size={28} /><h3 className="font-bold text-[#e8eef8]">{title}</h3><p className="mt-1 max-w-md text-sm text-[#8d9ab0]">{text}</p>{action && <div className="mt-4">{action}</div>}</div></div> }
export function ErrorState({ error, onRetry, conflict = false }: { error: string; onRetry?: () => void; conflict?: boolean }) { return <div className={`rounded-[6px] border p-4 text-sm ${conflict ? "border-amber-500/35 bg-amber-500/10 text-amber-100" : "border-rose-500/35 bg-rose-500/10 text-rose-100"}`} role="alert"><div className="flex items-start gap-3"><AlertTriangle size={18} className="mt-0.5 shrink-0" /><div className="flex-1"><strong>{conflict ? "Zwischenzeitlich geändert" : "Fehler"}</strong><p className="mt-1 opacity-85">{conflict ? "Der Datensatz wurde in einer anderen Sitzung geändert. Bitte neu laden und erneut prüfen." : error}</p></div>{onRetry && <Button onClick={onRetry}><RefreshCw size={13} className="mr-1 inline" />Neu laden</Button>}</div></div> }
export function Progress({ value, label }: { value: number; label: string }) { const safe = Math.max(0, Math.min(100, value)); return <div><div className="mb-1 flex justify-between text-xs text-[#9eacc0]"><span>{label}</span><strong>{Math.round(value)} %</strong></div><div className="h-2 overflow-hidden rounded-full bg-[#263247]" role="progressbar" aria-label={label} aria-valuenow={Math.round(value)}><div className="h-full bg-cyan-400" style={{ width: `${safe}%` }} /></div></div> }
