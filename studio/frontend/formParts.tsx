import { Loader2, Save, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

export const fieldCls = "mt-1 w-full rounded-[4px] border border-[#46617f] bg-[#111827] px-2 py-1 text-xs text-[#e8eef8] outline-none focus:border-[#69d7ff]"
const labelCls = "block text-[10px] font-bold uppercase tracking-wide text-[#68758a]"

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
      <button type="button" onClick={onSave} disabled={busy || !dirty} data-plan-save
        className="flex flex-1 items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 text-xs font-black text-[#08111c] disabled:opacity-40">
        {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} {dirty ? t("save") : t("saved")}
      </button>
      {onDelete && (
        <button type="button" onClick={onDelete} disabled={busy} data-plan-delete title={t("delete")} aria-label={t("delete")}
          className="rounded-[4px] border border-[#2a364b] p-1.5 text-[#ff6b8a] hover:border-[#ff6b8a] disabled:opacity-40">
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}
