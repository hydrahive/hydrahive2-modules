import { Check, Loader2, Save, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

export const fieldCls = "mt-1 w-full rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-xs text-[#e8eef8] outline-none focus:border-[#69d7ff]"
const labelCls = "block text-[10px] font-bold uppercase tracking-wide text-[#9aa7bc]"

/** Beschriftetes Eingabefeld (einzeilig oder mehrzeilig). */
export function Field({ label, value, onChange, rows, max, name }: {
  label: string; value: string; onChange: (v: string) => void; rows?: number; max: number; name: string
}) {
  return (
    <label className="block">
      <span className={labelCls}>{label}</span>
      {rows ? <textarea rows={rows} maxLength={max} value={value} onChange={(e) => onChange(e.target.value)} data-field={name} className={fieldCls} />
        : <input value={value} maxLength={max} onChange={(e) => onChange(e.target.value)} data-field={name} className={fieldCls} />}
    </label>
  )
}

export function Label({ children }: { children: React.ReactNode }) {
  return <span className={labelCls}>{children}</span>
}

/** Speichern (mit Rückmeldung über den Zustand `busy`) und optional Löschen. */
export function FormActions({ busy, dirty, onSave, onDelete }: { busy: boolean; dirty: boolean; onSave: () => void; onDelete?: () => void }) {
  const { t } = useTranslation("studio")
  return (
    <div className="flex items-center gap-2 pt-1">
      {dirty || busy ? (
        <button type="button" onClick={onSave} disabled={busy || !dirty} data-plan-save
          className="flex flex-1 items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 text-xs font-black text-[#08111c] disabled:opacity-40">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} {t("save")}
        </button>
      ) : (
        <span className="flex flex-1 items-center gap-1.5 py-1.5 text-xs text-[#7ee2a8]" data-plan-saved><Check size={13} /> {t("saved")}</span>
      )}
      {onDelete && (
        <button type="button" onClick={onDelete} disabled={busy} data-plan-delete
          className="flex items-center gap-1 rounded-[4px] border border-[#ff6b8a]/50 px-2 py-1.5 text-xs font-bold text-[#ff6b8a] hover:bg-[#ff6b8a]/10 disabled:opacity-40">
          <Trash2 size={13} /> {t("form_delete")}
        </button>
      )}
    </div>
  )
}
