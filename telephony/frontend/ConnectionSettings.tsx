import { Loader2, PhoneCall, PlugZap, Save, Trash2, Unplug } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ConnectionForm } from "./_ConnectionForm"
import { ConnectionStatusBox } from "./_ConnectionStatus"
import { SetupGuide } from "./SetupGuide"
import { telephonyApi } from "./api"
import { canSave, errorKey, formFrom, isDirty } from "./connectionLogic"
import type { Connection, ConnectionIn } from "./types"

type Busy = null | "save" | "connect" | "disconnect" | "delete"
const btn = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"

/** Einstellungen: Zugangsdaten, Speichern, Verbinden/Trennen, Status, Anleitung, Router-Hinweis. */
export function ConnectionSettings() {
  const { t } = useTranslation("voip")
  const [conn, setConn] = useState<Connection | null>(null)
  const [form, setForm] = useState<ConnectionIn>(formFrom(null))
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const apply = useCallback((c: Connection) => { setConn(c); setForm(formFrom(c)) }, [])

  useEffect(() => { void telephonyApi.connection().then(apply).catch(() => setError("unknown")) }, [apply])

  // Während „Verbindet …“ den Stand nachladen (der Server versucht es weiter)
  const status = conn?.status ?? "not_configured"
  useEffect(() => {
    if (status !== "connecting" && status !== "unreachable") return
    const id = window.setInterval(() => {
      void telephonyApi.connection().then((c) => setConn(c)).catch(() => undefined)
    }, 3000)
    return () => window.clearInterval(id)
  }, [status])

  const run = async (kind: Exclude<Busy, null>, fn: () => Promise<Connection | void>) => {
    setBusy(kind); setError(null); setSaved(false)
    try {
      const c = await fn()
      if (c) apply(c)
      if (kind === "save") setSaved(true)
    } catch (e) {
      setError(errorKey((e as { code?: string }).code))
    } finally {
      setBusy(null)
      setForm((f) => ({ ...f, password: "" }))
    }
  }

  const configured = conn?.configured === true
  const dirty = isDirty(form, conn)
  const remove = () => {
    if (!window.confirm(t("conn.delete_confirm"))) return
    void run("delete", async () => { await telephonyApi.deleteConnection(); return { configured: false, status: "not_configured" } })
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]" aria-labelledby="voip-conn-title">
      <div className="space-y-4">
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-5">
          <h2 id="voip-conn-title" className="flex items-center gap-2 font-semibold text-zinc-100">
            <PhoneCall size={18} className="text-indigo-300" /> {t("conn.title")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-400">{t("conn.intro")}</p>
          <p className="mt-2 text-xs leading-5 text-amber-200/80">{t("conn.stage_notice")}</p>
        </div>

        <ConnectionStatusBox status={status} />

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <ConnectionForm form={form} hasPassword={configured} disabled={busy !== null}
            onChange={(p) => { setSaved(false); setForm((f) => ({ ...f, ...p })) }} />

          {error && <p role="alert" className="mt-4 text-sm text-red-300">{t(`conn.errors.${error}`)}</p>}
          {saved && !error && <p className="mt-4 text-sm text-emerald-300">{t("conn.saved")}</p>}

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button type="button" data-voip-save="1" className={`${btn} bg-zinc-800 text-zinc-100 hover:bg-zinc-700`}
              disabled={busy !== null || !dirty || !canSave(form, configured)}
              onClick={() => void run("save", () => telephonyApi.saveConnection(form))}>
              {busy === "save" ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {busy === "save" ? t("conn.saving") : t("conn.save")}
            </button>
            {configured && conn.enabled ? (
              <button type="button" data-voip-disconnect="1" className={`${btn} bg-zinc-800 text-zinc-100 hover:bg-zinc-700`}
                disabled={busy !== null} onClick={() => void run("disconnect", telephonyApi.disconnect)}>
                <Unplug size={15} /> {t("conn.disconnect")}
              </button>
            ) : null}
            <button type="button" data-voip-connect="1" className={`${btn} bg-indigo-500 text-white hover:bg-indigo-400`}
              disabled={busy !== null || !configured || dirty} title={dirty ? t("conn.save_first") : undefined}
              onClick={() => void run("connect", telephonyApi.connect)}>
              {busy === "connect" ? <Loader2 size={15} className="animate-spin" /> : <PlugZap size={15} />}
              {busy === "connect" ? t("conn.connecting") : t("conn.connect")}
            </button>
            {configured && (
              <button type="button" data-voip-delete="1" onClick={remove} disabled={busy !== null}
                className={`${btn} ml-auto text-red-300 hover:bg-red-500/10`}>
                <Trash2 size={15} /> {t("conn.delete")}
              </button>
            )}
          </div>
          {dirty && configured && <p className="mt-2 text-xs text-zinc-500">{t("conn.save_first")}</p>}
        </div>
      </div>

      <SetupGuide form={form} />
    </section>
  )
}
