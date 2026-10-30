import { useTranslation } from "react-i18next"
import { errorKey } from "./logic"
import type { DeviceCode, GitHubState } from "./githubLogic"
import { BOX, BTN, BTN_MAIN } from "./ui"

interface Props { gh: GitHubState; code: DeviceCode | null; busy: boolean; onConnect: () => void; onDisconnect: () => void }

/** GitHub verbinden (Device-Flow): Code groß zeigen, Link zu GitHub, warten. Kein Passwort, kein Token-Eintippen. */
export function GitHubBoxView({ gh, code, busy, onConnect, onDisconnect }: Props) {
  const { t } = useTranslation("hydralabor")
  const link = "text-emerald-300 underline"
  return (
    <section className={BOX}>
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("github.title")}</h2>
      {gh.connected ? (
        <>
          <p className="text-sm text-emerald-300">{t("github.connected", { login: gh.login })}</p>
          <button type="button" className={BTN} disabled={busy} onClick={onDisconnect}>{t("github.disconnect")}</button>
          <p className="text-xs text-[#9aa7bc]">{t("github.revoke_hint")}{" "}
            <a className={link} href="https://github.com/settings/applications" target="_blank" rel="noreferrer">{t("github.revoke_link")}</a></p>
        </>
      ) : !gh.configured ? (
        <p className="text-sm text-[#c8d2df]">{t(errorKey("labor_github_not_configured"))}</p>
      ) : gh.pending && code ? (
        <div className="space-y-2" aria-live="polite">
          <p className="text-sm text-[#c8d2df]">{t("github.code_hint")}</p>
          <p className="select-all font-mono text-2xl tracking-widest text-[#e8eef8]">{code.user_code}</p>
          <div className="flex flex-wrap gap-2">
            <a className={`${BTN_MAIN} inline-block`} href={code.verification_uri} target="_blank" rel="noreferrer">{t("github.open")}</a>
            <button type="button" className={BTN} onClick={() => navigator.clipboard?.writeText(code.user_code)}>{t("github.copy")}</button>
          </div>
          <p className="text-sm text-amber-200">{t("github.waiting")}</p>
        </div>
      ) : (
        <>
          <p className="text-sm text-[#c8d2df]">{t("github.intro")}</p>
          <button type="button" className={BTN_MAIN} disabled={busy} onClick={onConnect}>{t("github.connect")}</button>
          <p className="text-xs text-[#9aa7bc]">{t("github.no_account")}{" "}
            <a className={link} href="https://github.com/signup" target="_blank" rel="noreferrer">{t("github.signup")}</a></p>
        </>
      )}
    </section>
  )
}
