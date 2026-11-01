import { useTranslation } from "react-i18next"
import type { Overview } from "./api"
import { errorKey, light, percentOfPlan, type Sample } from "./logic"
import { SampleChart } from "./SampleChart"
import { BOX, H2, LIGHT, MUTED, PATH_TEXT, WARN_MS } from "./ui"
import { when } from "./when"

function Lamp({ label, state, detail }: { label: string; state: string; detail: string }) {
  const { t } = useTranslation("network")
  return (
    <div className="flex items-center gap-3 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2">
      <span className={`h-3 w-3 shrink-0 rounded-full ${LIGHT[state]}`} aria-hidden />
      <div className="min-w-0">
        <div className="text-sm text-[#e8eef8]">{label}: {t(`light.${state}`)}</div>
        <div className="truncate text-xs text-[#c8d2df]">{detail}</div>
      </div>
    </div>
  )
}

const ms = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v)} ms`)

/** Anzeige der Übersicht (ohne Laden – gut testbar). */
export function OverviewView({ o, samples, canConfigure }: { o: Overview; samples: Sample[]; canConfigure: boolean }) {
  const { t, i18n } = useTranslation("network")
  const s = o.latest
  const sp = o.last_speedtest
  const down = percentOfPlan(sp?.down_mbit ?? null, o.plan.down)
  const up = percentOfPlan(sp?.up_mbit ?? null, o.plan.up)
  return (
    <div className="space-y-4" data-network-overview>
      {!o.configured && <p className="text-sm text-amber-300">{t(canConfigure ? "not_configured_admin" : "not_configured")}</p>}
      <section className={BOX}>
        {s ? <>
          <p className={`text-base font-semibold ${PATH_TEXT[s.path]}`}>{t("now", { path: t(`path.${s.path}`) })}</p>
          <p className="text-xs text-[#c8d2df]">{t("measured", { when: when(s.ts, i18n.language) })}</p>
          <div className="grid gap-2 sm:grid-cols-3">
            <Lamp label={t("section.home")} state={light(s.lan_loss, s.lan_rtt, WARN_MS.home)} detail={ms(s.lan_rtt)} />
            <Lamp label={t("section.fritz")} state={light(s.fritz_loss, s.fritz_rtt, WARN_MS.fritz)} detail={ms(s.fritz_rtt)} />
            <Lamp label={t("section.internet")} state={light(s.inet_loss, s.inet_rtt_avg, WARN_MS.internet)}
              detail={`${ms(s.inet_rtt_avg)} · ${s.inet_loss ?? "–"} %`} />
          </div>
        </> : <p className={MUTED}>{t("no_samples")}</p>}
      </section>
      <section className={BOX}>
        <h2 className={H2}>{t("chart.title")}</h2>
        <SampleChart samples={samples} />
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        <section className={BOX}>
          <h2 className={H2}>{t("speed.title")}</h2>
          {sp ? <div className="space-y-1 text-sm text-[#e8eef8]">
            <p>{t("speed.down")}: {t("speed.value", { v: sp.down_mbit ?? "–" })}{down !== null && <span className="text-[#c8d2df]"> · {t("speed.of_plan", { pct: down })}</span>}</p>
            <p className={up !== null && up < 50 ? "text-rose-300" : ""}>{t("speed.up")}: {t("speed.value", { v: sp.up_mbit ?? "–" })}{up !== null && <span> · {t("speed.of_plan", { pct: up })}</span>}</p>
            <p className="text-xs text-[#c8d2df]">{t("speed.at", { when: when(sp.ts, i18n.language) })}</p>
          </div> : <p className={MUTED}>{t("speed.none")}</p>}
        </section>
        <section className={BOX}>
          <h2 className={H2}>{t("udm.title")}</h2>
          {o.udm?.isp && <p className="text-sm text-[#e8eef8]">{t("udm.isp", { isp: o.udm.isp })}</p>}
          {o.counts && <p className="text-sm text-[#e8eef8]">{t("counts", { devices: o.counts.devices, online: o.counts.devices_online, clients: o.counts.clients, wireless: o.counts.wireless, wired: o.counts.wired })}</p>}
          {o.udm_at && <p className="text-xs text-[#c8d2df]">{t("measured", { when: when(o.udm_at, i18n.language) })}</p>}
          {o.udm_error && <p className="text-sm text-rose-300">{t("udm.error", { text: t(errorKey({ code: o.udm_error })) })}</p>}
          {!o.udm_at && !o.udm_error && <p className={MUTED}>{t("udm.never")}</p>}
        </section>
      </div>
    </div>
  )
}
