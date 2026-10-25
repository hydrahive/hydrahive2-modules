import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { ConnectionIn, Pbx } from "./types"

const input = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 disabled:opacity-60"

function Field({ label, help, children }: { label: string; help?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5 text-sm text-zinc-300">
      <span>{label}</span>
      {children}
      {help && <span className="block text-xs text-zinc-500">{help}</span>}
    </label>
  )
}

interface Props {
  form: ConnectionIn
  hasPassword: boolean
  disabled: boolean
  onChange: (patch: Partial<ConnectionIn>) => void
}

/** Alle Zugangsdaten. Das Kennwortfeld ist bei gespeichertem Kennwort leer (leer = behalten). */
export function ConnectionForm({ form, hasPassword, disabled, onChange }: Props) {
  const { t } = useTranslation("voip")
  const fritz = form.pbx === "fritzbox"
  const num = (v: string) => (v === "" ? 0 : Number(v))

  return (
    <fieldset disabled={disabled} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("conn.pbx")}>
          <select className={input} value={form.pbx} data-voip-field="pbx"
            onChange={(e) => onChange({ pbx: e.target.value as Pbx })}>
            <option value="fritzbox">{t("conn.pbx_fritzbox")}</option>
            <option value="sip">{t("conn.pbx_sip")}</option>
          </select>
        </Field>
        <Field label={t("conn.display_name")}>
          <input className={input} value={form.display_name} maxLength={80} data-voip-field="display_name"
            onChange={(e) => onChange({ display_name: e.target.value })} />
        </Field>
        <Field label={t("conn.registrar")} help={t("conn.registrar_help")}>
          <input className={input} value={form.registrar} maxLength={253} autoComplete="off" spellCheck={false}
            data-voip-field="registrar" onChange={(e) => onChange({ registrar: e.target.value.trim() })} />
        </Field>
        <Field label={t("conn.registrar_port")}>
          <input className={input} type="number" min={1} max={65535} value={form.registrar_port}
            data-voip-field="registrar_port" onChange={(e) => onChange({ registrar_port: num(e.target.value) })} />
        </Field>
        <Field label={t("conn.username")} help={fritz ? t("conn.username_help_fritzbox") : undefined}>
          <input className={input} value={form.username} maxLength={128} autoComplete="off" spellCheck={false}
            data-voip-field="username" onChange={(e) => onChange({ username: e.target.value.trim() })} />
        </Field>
        <Field label={t("conn.password")} help={fritz ? t("conn.password_help_fritzbox") : undefined}>
          <input className={input} type="password" value={form.password} maxLength={128} autoComplete="new-password"
            placeholder={hasPassword ? t("conn.password_keep") : ""} data-voip-field="password"
            onChange={(e) => onChange({ password: e.target.value })} />
        </Field>
        <Field label={t("conn.own_number")} help={t("conn.own_number_help")}>
          <input className={input} value={form.own_number} maxLength={30} inputMode="tel" data-voip-field="own_number"
            onChange={(e) => onChange({ own_number: e.target.value })} />
        </Field>
      </div>

      <details className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
        <summary className="cursor-pointer text-sm font-medium text-zinc-300">{t("conn.advanced")}</summary>
        <p className="mt-2 text-xs text-zinc-500">{t("conn.advanced_help")}</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <Field label={t("conn.local_sip_port")}>
            <input className={input} type="number" min={1024} max={65535} value={form.local_sip_port}
              data-voip-field="local_sip_port" onChange={(e) => onChange({ local_sip_port: num(e.target.value) })} />
          </Field>
          <Field label={t("conn.rtp_ports")}>
            <div className="flex items-center gap-2">
              <input className={input} type="number" min={1024} max={65534} step={2} value={form.rtp_port_min}
                data-voip-field="rtp_port_min" onChange={(e) => onChange({ rtp_port_min: num(e.target.value) })} />
              <span className="text-zinc-500">–</span>
              <input className={input} type="number" min={1025} max={65535} value={form.rtp_port_max}
                data-voip-field="rtp_port_max" onChange={(e) => onChange({ rtp_port_max: num(e.target.value) })} />
            </div>
          </Field>
          <Field label={t("conn.register_interval")}>
            <input className={input} type="number" min={60} max={3600} value={form.register_interval}
              data-voip-field="register_interval"
              onChange={(e) => onChange({ register_interval: num(e.target.value) })} />
          </Field>
        </div>
      </details>
    </fieldset>
  )
}
