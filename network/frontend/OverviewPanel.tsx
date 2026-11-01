import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getOverview, getSamples, type Overview } from "./api"
import type { Sample } from "./logic"
import { OverviewView } from "./OverviewView"

const REFRESH_MS = 60_000

/** Übersicht laden und jede Minute neu holen (so oft misst der Server). */
export function OverviewPanel({ canConfigure }: { canConfigure: boolean }) {
  const { t } = useTranslation("network")
  const [o, setO] = useState<Overview | null>(null)
  const [samples, setSamples] = useState<Sample[]>([])
  useEffect(() => {
    const load = () => Promise.all([getOverview(), getSamples(24)])
      .then(([ov, s]) => { setO(ov); setSamples(s.items) }).catch(() => {})
    load()
    const id = window.setInterval(load, REFRESH_MS)
    return () => window.clearInterval(id)
  }, [])
  if (!o) return <p className="text-sm text-[#c8d2df]">{t("loading")}</p>
  return <OverviewView o={o} samples={samples} canConfigure={canConfigure} />
}
