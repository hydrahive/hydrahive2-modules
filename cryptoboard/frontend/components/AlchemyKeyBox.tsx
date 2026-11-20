import { ExternalLink, KeyRound, Trash2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { cryptoApi } from "../api"
import { errorKey } from "../onchainImport"
import type { AlchemyKeyStatus } from "../types"

const C = "105 215 255"

// Alchemy-Key für den On-Chain-Trade-Import. Der Key steht nur im Eingabefeld
// (type=password) und geht einzig per PUT /alchemy-key raus; danach wird das Feld
// sofort geleert. Angezeigt wird nur der maskierte Status vom Backend.
export function AlchemyKeyBox() {
  const { t } = useTranslation("cryptoboard")
  const [status, setStatus] = useState<AlchemyKeyStatus | null>(null)
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const load = useCallback(async () => {
    try { setStatus(await cryptoApi.alchemyKeyStatus()) } catch { setStatus(null) }
  }, [])
  useEffect(() => { void load() }, [load])

  function fail(err: unknown) {
    const key = errorKey(err)
    setMsg({ ok: false, text: key ? t(key) : t("oc_err_generic") })
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) { setMsg({ ok: false, text: t("oc_err_alchemy_key_empty") }); return }
    setBusy(true)
    setMsg(null)
    try {
      setStatus(await cryptoApi.setAlchemyKey(input))
      setMsg({ ok: true, text: t("ak_saved") })
    } catch (err) {
      fail(err)
    } finally {
      setInput("") // Key nie länger als nötig im Speicher – auch bei Fehler leeren
      setBusy(false)
    }
  }

  async function remove() {
    if (!window.confirm(t("ak_confirm_delete"))) return
    setBusy(true)
    setMsg(null)
    try {
      await cryptoApi.deleteAlchemyKey()
      await load()
      setMsg({ ok: true, text: t("ak_deleted") })
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }

  const field = "flex-1 min-w-0 px-3 py-1.5 rounded-md bg-[rgb(var(--hh-s-box,21_28_43)/0.7)] border border-[rgb(var(--hh-s-rand,42_54_75))] text-sm text-[#e8eef8] placeholder-[#9aa7bc] outline-none"

  return (
    <div id="cryptoboard-alchemy-key">
      <CollapsibleBox boxId="cryptoboard-alchemy-key" color={C} icon={<KeyRound size={14} />} title={t("ak_title")}>
        <div className="box-b space-y-2.5">
          <p className="text-xs text-[#c8d2df]">
            {t("ak_status")}:{" "}
            {status?.set
              ? <span className="font-mono text-emerald-300">{status.masked ?? "…"}</span>
              : <span className="text-[#9aa7bc]">{t("ak_not_set")}</span>}
          </p>
          <form onSubmit={save} className="flex items-center gap-2">
            <input type="password" autoComplete="off" spellCheck={false} value={input}
              onChange={(e) => setInput(e.target.value)} placeholder={t("ak_placeholder")} className={field} />
            <button type="submit" disabled={busy || !input.trim()}
              className="px-3 py-1.5 rounded-md bg-emerald-500/20 text-emerald-300 text-sm hover:bg-emerald-500/30 disabled:opacity-50">
              {busy ? t("ak_testing") : t("ak_save")}
            </button>
            {status?.set && (
              <button type="button" onClick={remove} disabled={busy} aria-label={t("ak_delete")} title={t("ak_delete")}
                className="p-1.5 text-[#9aa7bc] hover:text-rose-400 disabled:opacity-50">
                <Trash2 size={15} />
              </button>
            )}
          </form>
          {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-rose-400"}`}>{msg.text}</p>}
          <p className="text-[11px] text-[#9aa7bc]">
            {t("ak_hint")}{" "}
            <a href="https://www.alchemy.com/" target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-sky-300 hover:underline">
              alchemy.com <ExternalLink size={10} />
            </a>
          </p>
        </div>
      </CollapsibleBox>
    </div>
  )
}
