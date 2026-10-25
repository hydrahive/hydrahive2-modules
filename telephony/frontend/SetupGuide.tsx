import { BookOpen, Router as RouterIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ConnectionIn } from "./types"

/** Anleitung (FRITZ!Box) und kurzer Hinweis für einen Router dazwischen – mit den gerade eingetragenen Ports. */
export function SetupGuide({ form }: { form: ConnectionIn }) {
  const { t } = useTranslation("voip")
  const steps = t("conn.guide.steps", { returnObjects: true }) as string[]
  const vars = { registrar_port: form.registrar_port, local_sip_port: form.local_sip_port,
    rtp_min: form.rtp_port_min, rtp_max: form.rtp_port_max }
  const points = t("conn.router.points", { returnObjects: true, ...vars }) as string[]

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5" data-voip-guide="1">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
          <BookOpen size={16} className="text-indigo-400" /> {t("conn.guide.title")}
        </h3>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-zinc-300">
          {Array.isArray(steps) && steps.map((s) => <li key={s}>{s}</li>)}
        </ol>
        <p className="mt-3 text-xs leading-5 text-zinc-500">{t("conn.guide.note")}</p>
      </section>

      <details className="group rounded-xl border border-zinc-800 bg-zinc-950/30 p-5" data-voip-router="1">
        <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold text-zinc-200">
          <RouterIcon size={16} className="text-amber-400" /> {t("conn.router.title")}
        </summary>
        <p className="mt-3 text-sm leading-6 text-zinc-400">{t("conn.router.intro")}</p>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-zinc-300">
          {Array.isArray(points) && points.map((p) => <li key={p}>{p}</li>)}
        </ul>
      </details>
    </div>
  )
}
