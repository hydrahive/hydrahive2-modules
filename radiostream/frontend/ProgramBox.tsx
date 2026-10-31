import { useTranslation } from "react-i18next"
import { parseProgramValue, programLine, programValue, type Mix, type Playlist, type Program } from "./programLogic"
import { BOX, INPUT } from "./ui"

interface Props { p: Program; playlists: Playlist[]; mixes: Mix[]; busy: boolean; onSet: (mode: string, ref: string) => void }

/** Reiter „Sender“: was läuft gerade (Alles / Playlist / Mix) und – mit Recht „Moderieren“ – umschalten. */
export function ProgramBox({ p, playlists, mixes, busy, onSet }: Props) {
  const { t } = useTranslation("radiostream")
  const line = programLine(p)
  return (
    <section className={BOX} data-radiostream-program>
      <h3 className="text-sm font-semibold text-[#e8eef8]">{t("program.heading")}</h3>
      <p className="text-sm text-emerald-300 break-words">{t(line.key, line.opts)}</p>
      {p.notice && <p className="text-sm text-amber-300" role="status">{t(`err.${p.notice}`)}</p>}
      {p.can_moderate && (
        <label className="block space-y-1">
          <span className="text-sm text-[#c8d2df]">{t("program.choose")}</span>
          <select value={programValue(p)} disabled={busy} className={INPUT}
            onChange={(e) => { const v = parseProgramValue(e.target.value); onSet(v.mode, v.ref_id) }}>
            <option value="all">{t("program.all")}</option>
            {playlists.length > 0 && <optgroup label={t("program.playlists")}>
              {playlists.map((x) => <option key={x.id} value={`playlist:${x.id}`}>{x.name}</option>)}</optgroup>}
            {mixes.length > 0 && <optgroup label={t("program.mixes")}>
              {mixes.map((x) => <option key={x.id} value={`mix:${x.id}`}>{x.name}</option>)}</optgroup>}
          </select>
          <span className="block text-xs text-[#9aa7bc]">{t("program.switch_hint")}</span>
        </label>)}
    </section>
  )
}
