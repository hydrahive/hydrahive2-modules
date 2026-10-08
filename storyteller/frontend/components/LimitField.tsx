// A1 – Kostengrenze je Auftrag (Spec kostengrenze.md §3): Schalter an/aus + Tokens, gespeichert im Buch
// (book.ghost.limit_tokens, 0 = aus). Gilt für Ghostwriter-Läufe, „Szene schreiben“ und Team-Aufträge.
// Kein vorbelegter Wert (keine festen Werte im Code): Einschalten öffnet das Feld, gespeichert wird erst eine
// gültige Zahl. Daneben ≈ Cent, wenn der Preis aus einer Schätzung bekannt ist. Leser sehen die Grenze nur.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { limitCents, parseLimit } from "../costLimit"
import type { BookState } from "../useBook"

const field = "rounded-lg border border-white/10 bg-zinc-950 px-2 py-1 text-sm text-zinc-100"

interface Props {
  state: BookState
  /** Schätzung des gerade gewählten Auftrags – nur für die Umrechnung in Cent. */
  price?: { input_tokens: number; output_tokens: number; cost_micros: number | null; model: string } | null
}

export function LimitField({ state, price }: Props) {
  const { t } = useTranslation("storyteller")
  const { book, canWrite } = state
  const saved = book.ghost.limit_tokens || 0
  // Nur was gerade getippt wird, liegt hier; sonst zeigt das Feld den gespeicherten Wert (auch nach Änderung von
  // außen, z. B. zweites Fenster). „opened“: eingeschaltet, aber noch keine gültige Zahl gespeichert.
  const [draft, setDraft] = useState<string | null>(null)
  const [opened, setOpened] = useState(false)
  const on = saved > 0 || opened
  const raw = draft ?? (saved ? String(saved) : "")
  const parsed = parseLimit(raw)
  const valid = parsed.ok && parsed.value > 0
  const save = (value: number) => {
    if (value !== saved) state.change((b) => ({ ...b, ghost: { ...b.ghost, limit_tokens: value } }))
  }
  const toggle = (next: boolean) => {
    setOpened(next)
    setDraft(null)
    if (!next) save(0)
  }
  const commit = () => {
    if (valid) { save(parsed.value); setDraft(null); setOpened(false) }
  }
  const cents = price && saved ? limitCents(price, saved) : null

  return (
    <fieldset className="st-limit space-y-1 text-xs text-zinc-400" disabled={!canWrite}>
      <legend className="mb-1">{t("run_limit")}</legend>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={on} onChange={(e) => toggle(e.target.checked)} />{t("run_limit_on")}
        </label>
        {on ? (
          <>
            <input type="text" inputMode="numeric" value={raw} aria-label={t("run_limit_tokens")} aria-invalid={!valid}
              autoFocus={!saved} className={`st-limit-input ${field} w-32 ${valid || raw === "" ? "" : "border-red-400/60"}`}
              onChange={(e) => setDraft(e.target.value)} onBlur={commit} />
            <span>{t("run_limit_tokens")}</span>
            {cents && <span className="text-zinc-500">{t("run_limit_cents", { cents, model: price?.model || t("ghost_model_default") })}</span>}
          </>
        ) : <span className="text-zinc-500">{t("run_limit_none")}</span>}
      </div>
      {on && !valid && raw !== "" && <p className="text-red-300">{t("run_limit_invalid")}</p>}
      <p className="text-[11px] text-zinc-500">{t("run_limit_help")}</p>
    </fieldset>
  )
}
