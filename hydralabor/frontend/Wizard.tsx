import { useTranslation } from "react-i18next"
import { CREATE_STEPS, errorKey, limitsError, progressOf, type Checks, type LabState, type Limits, type Model } from "./logic"
import { BOX, BTN, BTN_MAIN, INPUT } from "./ui"

interface Props {
  s: LabState; checks: Checks | null; models: Model[]; model: string; limits: Limits; busy: boolean; msg: string | null
  onCheck: () => void; onModel: (m: string) => void; onLimits: (l: Limits) => void; onCreate: () => void
}

/** Assistent (PLAN-L1.md): Voraussetzungen → Modell und Größe → Anlegen mit Fortschritt. Nur Anzeige, keine Abfragen. */
export function WizardView({ s, checks, models, model, limits, busy, msg, onCheck, onModel, onLimits, onCreate }: Props) {
  const { t } = useTranslation("hydralabor")
  const creating = s.running === "create"
  const limErr = limitsError(limits)
  const canCreate = !!checks?.ok && !!model && !limErr && !busy && !s.running
  const num = (k: keyof Limits, label: string) => (
    <label className="block space-y-1 text-sm text-zinc-300">
      <span>{label}</span>
      <input type="number" inputMode="numeric" className={INPUT} value={limits[k]} disabled={creating}
        onChange={(e) => onLimits({ ...limits, [k]: Number(e.target.value) })} />
    </label>
  )
  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-300">{t("wizard.intro")}</p>

      <section className={BOX}>
        <h2 className="text-sm font-semibold text-zinc-100">{t("wizard.s1")}</h2>
        {checks && (
          <ul className="space-y-1 text-sm">
            {checks.checks.map((c) => (
              <li key={c.id} className={c.ok ? "text-emerald-300" : "text-red-300"}>
                <span aria-hidden="true">{c.ok ? "✓ " : "✗ "}</span>{t(`check.${c.id}`)}
                {!c.ok && <span className="block pl-5 text-zinc-300">{t(errorKey(c.code))}
                  {c.have !== null && c.need !== null && <> ({t("check.have_need", { have: c.have, need: c.need })})</>}</span>}
              </li>
            ))}
          </ul>
        )}
        <button type="button" className={BTN} onClick={onCheck} disabled={busy || creating}>
          {busy && !checks ? t("wizard.rechecking") : t("wizard.check")}</button>
      </section>

      <section className={BOX}>
        <h2 className="text-sm font-semibold text-zinc-100">{t("wizard.s2")}</h2>
        <label className="block space-y-1 text-sm text-zinc-300">
          <span>{t("wizard.model")}</span>
          <select className={INPUT} value={model} disabled={creating} onChange={(e) => onModel(e.target.value)}>
            <option value="">{t("wizard.model_pick")}</option>
            {models.map((m) => <option key={m.id} value={m.id}>{m.label} ({m.provider})</option>)}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          {num("cpu", t("wizard.cpu"))}{num("ram_mb", t("wizard.ram"))}{num("disk_gb", t("wizard.disk"))}
        </div>
        {limErr && <p className="text-sm text-red-300">{t(limErr)}</p>}
      </section>

      <section className={BOX}>
        <h2 className="text-sm font-semibold text-zinc-100">{t("wizard.s3")}</h2>
        {creating ? <Progress s={s} /> : (
          <>
            {s.error_code && (
              <div role="alert" className="rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
                {t(errorKey(s.error_code))}
                {s.error_step && <span className="block">{t("wizard.failed_at", { step: t(`progress.${s.error_step}`) })}</span>}
              </div>
            )}
            <p className="text-sm text-zinc-400">{t("wizard.takes")}</p>
            <button type="button" className={BTN_MAIN} onClick={onCreate} disabled={!canCreate}>
              {s.error_code ? t("wizard.retry") : t("wizard.create")}</button>
          </>
        )}
        {msg && <p className="text-sm text-red-300">{t(msg)}</p>}
      </section>
    </div>
  )
}

function Progress({ s }: { s: LabState }) {
  const { t } = useTranslation("hydralabor")
  const p = progressOf(s)
  return (
    <div className="space-y-2">
      <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={p.pct} aria-label={t("job.create")}
        className="h-2 w-full overflow-hidden rounded bg-white/10">
        <div className="h-full bg-emerald-500 transition-all" style={{ width: `${Math.max(4, p.pct)}%` }} />
      </div>
      <ol className="space-y-0.5 text-sm">
        {CREATE_STEPS.map((k, i) => (
          <li key={k} className={i < p.index ? "text-emerald-300" : i === p.index ? "text-zinc-100" : "text-zinc-500"}>
            <span aria-hidden="true">{i < p.index ? "✓ " : i === p.index ? "… " : "· "}</span>{t(`progress.${k}`)}
          </li>
        ))}
      </ol>
      <p className="text-sm text-zinc-400">{t("wizard.takes")}</p>
    </div>
  )
}
