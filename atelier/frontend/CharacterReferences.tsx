import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { AtelierCharacter } from "./types"

interface Props {
  projectId: string
  character: AtelierCharacter
  onChanged: () => void
  refAbsPath: (rel: string) => string
}

/** Referenzbilder einer Figur: Vorschau-Galerie + Upload eigener Bilder. */
export function CharacterReferences({ projectId, character, onChanged, refAbsPath }: Props) {
  const { t } = useTranslation("atelier")
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await atelierApi.uploadReference(projectId, character.id, file)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  async function deleteRef(rel: string) {
    if (!window.confirm(t("delete_reference_confirm"))) return
    setBusy(true)
    setError(null)
    try {
      await atelierApi.deleteReference(projectId, character.id, rel)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const refs = character.references ?? []

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">
          {t("references")} ({refs.length}/3)
        </span>
        <button
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="text-xs px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-40"
        >
          {busy ? t("uploading") : t("upload_reference")}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={onPick}
          className="hidden"
        />
      </div>

      {refs.length > 0 && (
        <div className="flex gap-1.5 flex-wrap">
          {refs.map((rel) => (
            <div key={rel} className="group relative h-12 w-12">
              <img
                src={fileUrl(refAbsPath(rel))}
                alt=""
                title={refs.indexOf(rel) >= 3 ? t("reference_unused") : undefined}
                className={`h-12 w-12 rounded object-cover border ${
                  refs.indexOf(rel) >= 3 ? "border-slate-700 opacity-40" : "border-emerald-600"
                }`}
              />
              <button
                type="button"
                onClick={() => deleteRef(rel)}
                disabled={busy}
                title={t("delete_reference")}
                className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full border border-red-400/60 bg-red-600 text-[11px] leading-none text-white opacity-0 shadow transition-opacity group-hover:opacity-100 focus:opacity-100 disabled:opacity-40"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="text-[10px] text-slate-500">{t("reference_hint")}</p>
      {error && <div className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{error}</div>}
    </div>
  )
}
