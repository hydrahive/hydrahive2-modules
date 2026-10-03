import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Copy } from "lucide-react"
import { miningApi, type Pairing } from "../api"
import { isValidRigName } from "../rigState"

export function PairDialog({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation("mining")
  const [name, setName] = useState("")
  const [pairing, setPairing] = useState<Pairing | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const valid = isValidRigName(name)

  const create = async () => {
    setError(null)
    try { setPairing(await miningApi.pair(name)) } catch (e) { setError(String(e)) }
  }
  const copy = async () => {
    if (!pairing) return
    try { await navigator.clipboard.writeText(pairing.command); setCopied(true) } catch { setCopied(false) }
  }

  return (
    <div className="space-y-3 rounded-xl border border-emerald-500/30 bg-zinc-900/60 p-4">
      <h3 className="text-sm font-semibold text-zinc-100">{t("pair_title")}</h3>
      {!pairing && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 space-y-1 text-xs text-zinc-400">
            <span>{t("rig_name")}</span>
            <input value={name} maxLength={32} placeholder="rig-01" onChange={(e) => setName(e.target.value.toLowerCase())}
              className="w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
          </label>
          <button onClick={create} disabled={!valid}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-500 disabled:opacity-40">
            {t("pair_create")}
          </button>
          <button onClick={onDone} className="rounded-lg px-3 py-2 text-sm text-zinc-400 hover:bg-white/5">{t("cancel")}</button>
          {name && !valid && <p className="w-full text-xs text-amber-300">{t("rig_name_hint")}</p>}
        </div>
      )}
      {pairing && (
        <div className="space-y-2 text-sm">
          <p className="text-zinc-300">{t("pair_step1", { name: pairing.name })}</p>
          <div className="flex items-start gap-2">
            <code className="flex-1 break-all rounded-lg bg-zinc-950 p-3 text-xs text-emerald-200">{pairing.command}</code>
            <button onClick={copy} title={t("copy")} className="rounded-lg p-2 text-zinc-300 hover:bg-white/10"><Copy size={16} /></button>
          </div>
          {copied && <p className="text-xs text-emerald-300">{t("copied")}</p>}
          <p className="text-xs text-zinc-500">
            {t("pair_code")}: <b className="text-zinc-300">{pairing.code}</b> · {t("pair_valid_until", { time: new Date(pairing.expires_at).toLocaleTimeString() })}
            {pairing.pin ? ` · ${t("pair_pinned")}` : ""}
          </p>
          <p className="text-zinc-300">{t("pair_step2")}</p>
          <button onClick={onDone} className="rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700">{t("done")}</button>
        </div>
      )}
      {error && <p className="text-xs text-rose-300">{error}</p>}
    </div>
  )
}
