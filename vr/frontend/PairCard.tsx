import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { vrApi, type Pairing } from "./api"
import { QrCode } from "./QrCode"

/** QR anzeigen, Ablauf herunterzählen, nach Kopplung die Liste neu laden lassen. */
export function PairCard({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation("vr")
  const [name, setName] = useState("Quest 3")
  const [pairing, setPairing] = useState<Pairing | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [left, setLeft] = useState(0)

  useEffect(() => {
    if (!pairing) return
    const end = new Date(pairing.expires_at).getTime()
    const tick = () => setLeft(Math.max(0, Math.round((end - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    const poll = setInterval(onDone, 4000)          // neu gekoppelte Brille in der Liste zeigen
    return () => { clearInterval(id); clearInterval(poll) }
  }, [pairing, onDone])

  const create = async () => {
    setError(null)
    try { setPairing(await vrApi.pair(name.trim() || "Quest")) } catch (e) { setError(String(e)) }
  }

  if (!pairing) {
    return (
      <div className="space-y-3 rounded-xl border border-amber-500/30 bg-zinc-900/60 p-4">
        <h3 className="text-sm font-semibold text-zinc-100">{t("pair_title")}</h3>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 space-y-1 text-xs text-zinc-400">
            <span>{t("headset_name")}</span>
            <input value={name} maxLength={40} onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
          </label>
          <button onClick={create} className="rounded-lg bg-amber-600 px-3 py-2 text-sm text-white hover:bg-amber-500">
            {t("pair_create")}
          </button>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    )
  }
  const mm = Math.floor(left / 60)
  const ss = String(left % 60).padStart(2, "0")
  return (
    <div className="flex flex-wrap items-center gap-5 rounded-xl border border-amber-500/30 bg-zinc-900/60 p-4">
      {left > 0 ? <QrCode matrix={pairing.qr} /> : <div className="grid h-[280px] w-[280px] place-items-center rounded-lg bg-zinc-800 text-sm text-zinc-400">{t("expired")}</div>}
      <div className="flex-1 space-y-2 text-sm text-zinc-300">
        <p>{t("step1")}</p>
        <p>{t("step2")}</p>
        <p className="text-xs text-zinc-500">{t("valid_for", { time: `${mm}:${ss}` })} · {t("code")}: <span className="font-mono">{pairing.code}</span></p>
        {pairing.pinned && <p className="text-xs text-emerald-400">{t("pinned")}</p>}
        <p className="text-xs text-zinc-500">{t("no_key_in_qr")}</p>
        <div className="flex gap-2 pt-1">
          {left === 0 && <button onClick={create} className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs text-white">{t("new_code")}</button>}
          <button onClick={() => setPairing(null)} className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 hover:bg-white/5">{t("close")}</button>
        </div>
      </div>
    </div>
  )
}
