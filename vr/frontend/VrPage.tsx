import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { vrApi, type Headset } from "./api"
import { PairCard } from "./PairCard"

/** VR-Brillen: koppeln per QR, gekoppelte Brillen sehen und entfernen. Jeder nur seine eigenen. */
export function VrPage() {
  const { t } = useTranslation("vr")
  const [headsets, setHeadsets] = useState<Headset[]>([])
  const [online, setOnline] = useState(0)
  const [pairing, setPairing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setHeadsets(await vrApi.headsets())
      setOnline((await vrApi.status()).headsets)
    } catch (e) { setError(String(e)) }
  }, [])
  useEffect(() => { void load() }, [load])

  const remove = async (h: Headset) => {
    if (!confirm(t("remove_confirm", { name: h.name }))) return
    await vrApi.remove(h.id)
    void load()
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500">{t("subtitle")}</p>
        </div>
        {!pairing && (
          <button onClick={() => setPairing(true)} className="rounded-lg bg-amber-600 px-3 py-2 text-sm text-white hover:bg-amber-500">
            {t("pair_button")}
          </button>
        )}
      </div>
      {pairing && <PairCard onDone={() => { void load() }} />}
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="rounded-xl border border-white/10 bg-zinc-900/60">
        <div className="flex items-center justify-between border-b border-white/5 px-4 py-2 text-xs text-zinc-400">
          <span>{t("headsets")}</span>
          <span>{t("online", { count: online })}</span>
        </div>
        {headsets.length === 0 && <p className="px-4 py-6 text-sm text-zinc-500">{t("empty")}</p>}
        {headsets.map((h) => (
          <div key={h.id} className="flex items-center justify-between border-b border-white/5 px-4 py-3 last:border-0">
            <div>
              <p className="text-sm text-zinc-100">🥽 {h.name}</p>
              <p className="text-xs text-zinc-500">{t("paired_at", { time: new Date(h.paired_at).toLocaleString() })}</p>
            </div>
            <button onClick={() => remove(h)} className="rounded-lg px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10">{t("remove")}</button>
          </div>
        ))}
      </div>
    </div>
  )
}
