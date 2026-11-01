import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getCreds, getSettings, saveSettings, type Cred, type Settings } from "./api"
import { CertBox } from "./CertBox"
import { errorKey, looksLikeUdmUrl } from "./logic"
import { SyncBox } from "./SyncBox"
import { BOX, BTN_MAIN, H2, INPUT, MUTED } from "./ui"

type Form = { udm_url: string; udm_credential: string; fritz_host: string; fritz_credential: string; down: string; up: string; price: string }
const num = (v: string) => (v.trim() === "" ? null : Number(v.replace(",", ".")))
const str = (v: number | null) => (v === null || v === undefined ? "" : String(v))

function fromSettings(s: Settings): Form {
  return { udm_url: s.udm_url ?? "", udm_credential: s.udm_credential ?? "", fritz_host: s.fritz_host ?? "",
    fritz_credential: s.fritz_credential ?? "", down: str(s.plan_down_mbit), up: str(s.plan_up_mbit), price: str(s.plan_price_eur) }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{label}</span>{children}</label>
}

/** Einrichtung: Zugänge nur als Name aus dem Safe (nie ein Passwortfeld hier), Tarif, Zertifikat, Abruf, Import. */
export function SettingsPanel({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation("network")
  const [f, setF] = useState<Form | null>(null)
  const [saved, setSaved] = useState<Settings | null>(null)
  const [creds, setCreds] = useState<Cred[]>([])
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    Promise.all([getSettings(), getCreds()]).then(([s, c]) => { setSaved(s); setF(fromSettings(s)); setCreds(c.items) }).catch(() => {})
  }, [])
  if (!f) return <p className={MUTED}>{t("loading")}</p>
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const keys = creds.filter((c) => c.type !== "basic")
  const logins = creds.filter((c) => c.type === "basic")
  const save = () => {
    setBusy(true); setMsg(null)
    saveSettings({ udm_url: f.udm_url.trim(), udm_credential: f.udm_credential, fritz_host: f.fritz_host.trim(),
      fritz_credential: f.fritz_credential, plan_down_mbit: num(f.down), plan_up_mbit: num(f.up), plan_price_eur: num(f.price) })
      .then((s) => { setSaved(s); setMsg({ ok: true, text: t("settings.saved") }); onSaved() })
      .catch((e) => setMsg({ ok: false, text: t(errorKey(e)) }))
      .finally(() => setBusy(false))
  }
  return (
    <div className="max-w-3xl space-y-4" data-network-settings>
      <div><h2 className={H2}>{t("settings.heading")}</h2><p className={MUTED}>{t("settings.hint")}</p></div>
      <section className={BOX}>
        <h3 className={H2}>{t("settings.udm")}</h3>
        <Field label={t("settings.udm_url")}>
          <input value={f.udm_url} onChange={set("udm_url")} placeholder={t("settings.udm_url_example")} spellCheck={false} className={INPUT} />
        </Field>
        <Field label={t("settings.udm_cred")}>
          <select value={f.udm_credential} onChange={set("udm_credential")} className={INPUT}>
            <option value="">{t("settings.choose")}</option>
            {keys.map((c) => <option key={c.name} value={c.name}>{c.name} – {c.url_pattern}</option>)}
          </select>
          {keys.length === 0 && <span className="text-xs text-[#c8d2df]">{t("settings.no_creds")}</span>}
        </Field>
      </section>
      <section className={BOX}>
        <h3 className={H2}>{t("settings.fritz")}</h3>
        <Field label={t("settings.fritz_host")}>
          <input value={f.fritz_host} onChange={set("fritz_host")} placeholder={t("settings.fritz_host_example")} spellCheck={false} className={INPUT} />
        </Field>
        <Field label={t("settings.fritz_cred")}>
          <select value={f.fritz_credential} onChange={set("fritz_credential")} className={INPUT}>
            <option value="">{t("settings.none_cred")}</option>
            {logins.map((c) => <option key={c.name} value={c.name}>{c.name} – {c.url_pattern}</option>)}
          </select>
        </Field>
      </section>
      <section className={BOX}>
        <h3 className={H2}>{t("settings.plan")}</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label={t("settings.plan_down")}><input inputMode="decimal" value={f.down} onChange={set("down")} className={INPUT} /></Field>
          <Field label={t("settings.plan_up")}><input inputMode="decimal" value={f.up} onChange={set("up")} className={INPUT} /></Field>
          <Field label={t("settings.plan_price")}><input inputMode="decimal" value={f.price} onChange={set("price")} className={INPUT} /></Field>
        </div>
      </section>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className={BTN_MAIN} disabled={busy || !looksLikeUdmUrl(f.udm_url) || !f.udm_credential} onClick={save}>{t("settings.save")}</button>
        {msg && <span role="status" className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`}>{msg.text}</span>}
      </div>
      {saved?.udm_url && <CertBox confirmed={!!saved.udm_pin} onChange={setSaved} />}
      {saved?.udm_pin && <SyncBox />}
    </div>
  )
}
