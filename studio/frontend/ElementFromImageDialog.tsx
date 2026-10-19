import { useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fieldCls } from "./formParts"
import { Backdrop } from "./StudioDialogs"

interface Props {
  kind: "character" | "place"
  suggestion: string
  busy: boolean
  onConfirm: (name: string) => void
  onClose: () => void
}

/** Bibliothek → „Als Figur/Ort anlegen …“ (C2): nur den Namen fragen; das Bild wird Vorlage, die KI beschreibt es. */
export function ElementFromImageDialog({ kind, suggestion, busy, onConfirm, onClose }: Props) {
  const { t } = useTranslation("studio")
  const [name, setName] = useState(suggestion)
  return (
    <Backdrop onClose={onClose} label={t(`media_as_${kind}`)}>
      <form className="space-y-3 p-4 text-xs text-[#c3ccdd]" onSubmit={(e) => { e.preventDefault(); if (name.trim()) onConfirm(name.trim()) }}>
        <label className="block"><span className="text-sm text-[#e8eef8]">{t("media_as_name")}</span>
          <input autoFocus value={name} maxLength={200} onChange={(e) => setName(e.target.value)} className={fieldCls} data-media-as-name />
        </label>
        <p className="leading-relaxed text-[#8d9ab0]">{t("media_as_hint")}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="submit" disabled={busy || !name.trim()} data-media-as-confirm
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy && <Loader2 size={13} className="animate-spin" />} {t("media_as_create")}
          </button>
        </div>
      </form>
    </Backdrop>
  )
}
