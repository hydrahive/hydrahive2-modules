import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getCredentials, getSource, saveSource, startScan, testSource } from "./api"
import { errorKey, isSmbUrl, matchCredential } from "./logic"

/** Musikquelle: Adresse + Zugang aus dem Safe (nie ein Passwortfeld hier). Nur Admins. */
export function SettingsPanel({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation("radiostream")
  const [url, setUrl] = useState("")
  const [cred, setCred] = useState("")
  const [creds, setCreds] = useState<{ name: string; url_pattern: string }[]>([])
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    Promise.all([getSource(), getCredentials()]).then(([s, c]) => {
      setCreds(c.items)
      setUrl(s.url ?? "")
      setCred(s.credential_name ?? matchCredential(c.items, s.url ?? "") ?? "")
    }).catch(() => {})
  }, [])

  // Passenden Safe-Eintrag zur getippten Adresse vorbelegen, solange noch keiner gewählt ist
  const onUrl = (v: string) => {
    setUrl(v)
    if (!cred) setCred(matchCredential(creds, v) ?? "")
  }

  const valid = isSmbUrl(url) && !!cred
  const run = (fn: () => Promise<void>) => { setBusy(true); setMsg(null); fn().finally(() => setBusy(false)) }
  const test = () => run(() => testSource(url.trim(), cred)
    .then((r) => setMsg({ ok: true, text: t("settings.test_ok", { count: r.top_dirs }) }))
    .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })))
  const save = () => run(() => saveSource(url.trim(), cred)
    .then(() => { setMsg({ ok: true, text: t("settings.saved") }); onSaved() })
    .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })))
  const scanNow = () => run(() => saveSource(url.trim(), cred).then(() => startScan())
    .then(() => { setMsg({ ok: true, text: t("scan.started") }); onSaved() })
    .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })))

  return (
    <section className="max-w-2xl space-y-4" data-radiostream-settings>
      <div>
        <h2 className="text-base font-semibold text-zinc-100">{t("settings.heading")}</h2>
        <p className="text-sm text-zinc-400">{t("settings.hint")}</p>
      </div>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("settings.url")}</span>
        <input value={url} onChange={(e) => onUrl(e.target.value)} placeholder={t("settings.url_example")} spellCheck={false}
          className="w-full rounded border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100" />
        {url && !isSmbUrl(url) && <span className="text-xs text-amber-300">{t("settings.invalid_url")}</span>}
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-zinc-300">{t("settings.credential")}</span>
        <select value={cred} onChange={(e) => setCred(e.target.value)} className="w-full rounded border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100">
          <option value="">{t("settings.choose")}</option>
          {creds.map((c) => <option key={c.name} value={c.name}>{c.name} – {c.url_pattern}</option>)}
        </select>
        {creds.length === 0 && <span className="text-xs text-zinc-400">{t("settings.none")}</span>}
      </label>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={!valid || busy} onClick={test} className="rounded border border-white/15 px-3 py-1.5 text-sm text-zinc-200 hover:bg-white/10 disabled:opacity-40">{t("settings.test")}</button>
        <button type="button" disabled={!valid || busy} onClick={save} className="rounded border border-white/15 px-3 py-1.5 text-sm text-zinc-200 hover:bg-white/10 disabled:opacity-40">{t("settings.save")}</button>
        <button type="button" disabled={!valid || busy} onClick={scanNow} className="rounded bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-500 disabled:opacity-40">{t("settings.scan_now")}</button>
      </div>
      {msg && <p className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`} role="status">{msg.text}</p>}
      <p className="text-xs text-zinc-500">{t("settings.nightly")}</p>
    </section>
  )
}
