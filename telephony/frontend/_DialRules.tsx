import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Switch } from "./_Switch"
import { telephonyApi } from "./api"
import { dialErrorKey } from "./dialLogic"
import type { Connection } from "./types"

type Configured = Extract<Connection, { configured: true }>

/** Freigaben für Sondernummern und Ausland (Standard aus). Notruf ist nie wählbar – dafür gibt es keinen Schalter. */
export function DialRules({ conn, onError }: { conn: Configured; onError: (key: string | null) => void }) {
  const { t } = useTranslation("voip")
  const [premium, setPremium] = useState(conn.allow_premium)
  const [foreign, setForeign] = useState(conn.allow_foreign)
  const save = async (p: boolean, f: boolean) => {
    const before = [premium, foreign]
    setPremium(p); setForeign(f); onError(null)
    try { await telephonyApi.saveDialRules(p, f) }
    catch (e) { setPremium(before[0]); setForeign(before[1]); onError(dialErrorKey((e as { code?: string }).code)) }
  }
  return (
    <div className="space-y-3 border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-4">
      <p className="text-sm font-medium text-[#c8d2df]">{t("dial.rules_title")}</p>
      <div className="flex items-center gap-3 text-sm text-[#c8d2df]" data-voip-allow="premium">
        <Switch checked={premium} label={t("dial.allow_premium")} onChange={(v) => void save(v, foreign)} />
        {t("dial.allow_premium")}
      </div>
      <div className="flex items-center gap-3 text-sm text-[#c8d2df]" data-voip-allow="foreign">
        <Switch checked={foreign} label={t("dial.allow_foreign")} onChange={(v) => void save(premium, v)} />
        {t("dial.allow_foreign")}
      </div>
      <p className="text-xs text-[#9aa7bc]">{t("dial.rules_help")}</p>
    </div>
  )
}
