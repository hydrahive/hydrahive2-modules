import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getGenres, getStats, getTracks, type Stats, type Track } from "./api"
import { Filters } from "./Filters"
import { audioUrl, errorKey, type Filter } from "./logic"
import { ScanBox } from "./ScanBox"
import { StatsBar } from "./StatsBar"
import { TrackRow } from "./TrackRow"
import { TrackActions } from "./TrackActions"
import { enqueue, addToPlaylist, addSearchToPlaylist } from "./api"
import { programErrorKey, type Playlist } from "./programLogic"

const EMPTY: Filter = { q: "", genre: "", decade: "", format: "", missing: false }

/** Reiter Bibliothek: Zahlen, Stand des Einlesens, Suche/Filter, Liste (seitenweise, 200 je Abruf), Vorhören. */
export function Library({ isAdmin, configured, canModerate = false, playlists = [] }: { isAdmin: boolean; configured: boolean; canModerate?: boolean; playlists?: Playlist[] }) {
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
  const [menu, setMenu] = useState<string | null>(null)
  const [target, setTarget] = useState("")
  const act = (fn: () => Promise<unknown>, ok: string) => { setMenu(null); fn().then(() => setMsg(t(ok))).catch((e) => setMsg(t(programErrorKey(e)))) }
  const searchBody = () => ({ q: f.q.trim(), genre: f.genre, format: f.format,
    ...(f.decade ? { year_from: Number(f.decade), year_to: Number(f.decade) + 9 } : {}) })

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
      {msg && <p className="text-sm text-[#c8d2df]" role="status">{msg}</p>}
      {canModerate && playlists.length > 0 && filtered && !f.missing && (items?.length ?? 0) > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <select value={target} onChange={(e) => setTarget(e.target.value)} aria-label={t("playlist.add_all")}
            className="rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-2 py-1.5 text-sm text-[#e8eef8]">
            <option value="">{t("track.add_to")} …</option>
            {playlists.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button type="button" disabled={!target} onClick={() => act(async () => { const r = await addSearchToPlaylist(target, searchBody()); setMsg(t("playlist.added", { count: r.added })) }, "track.added")}
            className="rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] disabled:opacity-40">{t("playlist.add_all")}</button>
        </div>)}
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
                  {canModerate && <th className="w-10" />}
                </tr>
              </thead>
              <tbody>{items.map((it) => <TrackRow key={it.track_id} t={it} playing={playing === it.track_id} onPlay={play}
                actions={canModerate ? <TrackActions trackId={it.track_id} playlists={playlists} open={menu === it.track_id}
                  onToggle={() => setMenu(menu === it.track_id ? null : it.track_id)}
                  onQueue={(id, front) => act(() => enqueue(id, front), "track.queued")}
                  onAdd={(pid, id) => act(() => addToPlaylist(pid, [id]), "track.added")} /> : undefined} />)}</tbody>
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
