import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getSettings, saveSettings, testConnection, type TvSettings } from "./api"
import { errorKey, isLocalAddress } from "./logic"

const INPUT = "w-full rounded border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"

/** Einrichten (nur Admins): Name, Adresse, Schlüssel. Der Schlüssel kommt nie zurück – nur „gespeichert“. */
export function Setup({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation("fernseher")
  const [cfg, setCfg] = useState<TvSettings | null>(null)
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const [psk, setPsk] = useState("")
  const [limit, setLimit] = useState(60)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getSettings().then((s) => { setCfg(s); setName(s.name); setAddress(s.address); setLimit(s.volume_limit) }).catch(() => {})
  }, [])

  const needsPsk = !cfg?.psk_set
  const valid = isLocalAddress(address) && (!needsPsk || psk.trim().length > 0) && limit >= 1 && limit <= 100
  const run = (fn: () => Promise<void>) => { setBusy(true); setMsg(null); fn().finally(() => setBusy(false)) }
  const save = () => run(() => saveSettings({ name, address, psk, volume_limit: limit })
    .then((s) => { setCfg(s); setPsk(""); setMsg({ ok: true, text: t("setup.saved") }); onSaved() })
    .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })))
  const test = () => run(() => testConnection()
    .then((r) => setMsg({ ok: true, text: t("setup.test_ok", { model: r.model, power: t(r.power === "on" ? "setup.power_on" : "setup.power_standby") }) }))
    .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })))

  return (
    <section className="space-y-3 rounded-xl border border-white/10 bg-zinc-900 p-4" data-tv-setup>
      <h2 className="text-base font-semibold text-zinc-100">{t("setup.heading")}</h2>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("setup.name")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("setup.name_example")} maxLength={80} className={INPUT} />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("setup.address")}</span>
        <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder={t("setup.address_example")} spellCheck={false} className={INPUT} />
        {address && !isLocalAddress(address) && <span className="text-xs text-amber-300">{t("setup.address_hint")}</span>}
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("setup.psk")}</span>
        <input type="password" autoComplete="new-password" value={psk} onChange={(e) => setPsk(e.target.value)} className={INPUT} />
        <span className="block text-xs text-zinc-400">{cfg?.psk_set ? t("setup.psk_set") : t("setup.psk_hint")}</span>
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("setup.limit")}</span>
        <input type="number" min={1} max={100} value={limit} onChange={(e) => setLimit(Number(e.target.value))} className={`${INPUT} w-28`} />
      </label>
      {msg && <p role="status" className={`text-sm ${msg.ok ? "text-emerald-300" : "text-amber-300"}`}>{msg.text}</p>}
      <div className="flex flex-wrap gap-2">
        <button disabled={busy || !valid} onClick={save} className="min-h-11 rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-40">{t("setup.save")}</button>
        <button disabled={busy || !cfg?.configured} onClick={test} className="min-h-11 rounded-lg bg-zinc-800 px-4 py-2 text-sm text-zinc-100 disabled:opacity-40">{t("setup.test")}</button>
      </div>
    </section>
  )
}
