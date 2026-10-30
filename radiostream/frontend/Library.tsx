import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getGenres, getStats, getTracks, type Stats, type Track } from "./api"
import { Filters } from "./Filters"
import { audioUrl, errorKey, type Filter } from "./logic"
import { ScanBox } from "./ScanBox"
import { StatsBar } from "./StatsBar"
import { TrackRow } from "./TrackRow"

const EMPTY: Filter = { q: "", genre: "", decade: "", format: "", missing: false }

/** Reiter Bibliothek: Zahlen, Stand des Einlesens, Suche/Filter, Liste (seitenweise, 200 je Abruf), Vorhören. */
export function Library({ isAdmin, configured }: { isAdmin: boolean; configured: boolean }) {
  const { t } = useTranslation("radiostream")
  const token = useAuthStore((s: { token?: string | null }) => s.token) ?? ""
  const [f, setF] = useState<Filter>(EMPTY)
  const [items, setItems] = useState<Track[] | null>(null)
  const [cursor, setCursor] = useState<string | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [genres, setGenres] = useState<string[]>([])
  const [playing, setPlaying] = useState<string | null>(null)
  const [msg, setMsg] = useState("")
  const audio = useRef<HTMLAudioElement | null>(null)

  const loadMeta = useCallback(() => {
    getStats().then(setStats).catch(() => {})
    getGenres().then((r) => setGenres(r.items.map((g) => g.genre))).catch(() => {})
  }, [])
  const load = useCallback(() => {
    getTracks(f, "").then((r) => { setItems(r.items); setCursor(r.next_cursor); setMsg("") })
      .catch((e) => { setItems([]); setMsg(t(errorKey(e))) })
  }, [f, t])
  const more = () => cursor && getTracks(f, cursor).then((r) => { setItems((old) => [...(old ?? []), ...r.items]); setCursor(r.next_cursor) })
    .catch((e) => setMsg(t(errorKey(e))))

  useEffect(() => { loadMeta() }, [loadMeta])
  useEffect(() => { const h = setTimeout(load, 250); return () => clearTimeout(h) }, [load])

  const play = (id: string) => {
    const el = audio.current
    if (!el) return
    if (playing === id) { el.pause(); setPlaying(null); return }
    el.src = audioUrl(id, token)
    el.play().then(() => setPlaying(id)).catch(() => setMsg(t("err.radiostream_track_unavailable")))
  }
  const refresh = useCallback(() => { loadMeta(); load() }, [loadMeta, load])
  const filtered = f.q || f.genre || f.decade || f.format || f.missing

  return (
    <div className="space-y-3">
      {stats && stats.tracks > 0 && <StatsBar stats={stats} />}
      <ScanBox isAdmin={isAdmin} configured={configured} onFinished={refresh} />
      <Filters f={f} genres={genres} onChange={setF} />
      {msg && <p className="text-sm text-rose-300">{msg}</p>}
      <audio ref={audio} onEnded={() => setPlaying(null)} onPause={() => setPlaying(null)} className="hidden" preload="none" />
      {items === null ? <p className="text-sm text-[#9aa7bc]">{t("loading")}</p>
        : items.length === 0 ? (
          <div className="rounded border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] p-6 text-sm text-[#c8d2df]" data-radiostream-empty>
            {filtered ? t("empty_search") : <>{t("empty")} {isAdmin ? t("empty_admin") : t("empty_user")}</>}
          </div>
        ) : (
          <div className="overflow-hidden rounded border border-[rgb(var(--hh-s-rand,42_54_75))]">
            <table className="w-full table-fixed">
              <thead className="bg-[rgb(var(--hh-s-innen,17_24_39))] text-left text-xs uppercase tracking-wide text-[#9aa7bc]">
                <tr>
                  <th className="w-10" />
                  <th className="py-2 pr-3">{t("col.title")}</th>
                  <th className="hidden py-2 pr-3 md:table-cell">{t("col.artist")}</th>
                  <th className="hidden py-2 pr-3 lg:table-cell">{t("col.album")}</th>
                  <th className="hidden w-16 py-2 pr-3 md:table-cell">{t("col.year")}</th>
                  <th className="w-20 py-2 pr-3 text-right">{t("col.length")}</th>
                  <th className="hidden w-16 py-2 pr-2 sm:table-cell">{t("col.format")}</th>
                </tr>
              </thead>
              <tbody>{items.map((it) => <TrackRow key={it.track_id} t={it} playing={playing === it.track_id} onPlay={play} />)}</tbody>
            </table>
            {cursor && (
              <div className="border-t border-[rgb(var(--hh-s-rand,42_54_75))] p-2 text-center">
                <button type="button" onClick={more} className="rounded px-3 py-1 text-sm text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{t("more")}</button>
              </div>
            )}
          </div>
        )}
    </div>
  )
}
