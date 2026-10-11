import { useState } from "react"
import { useTranslation } from "react-i18next"
import { tonstudioApi } from "./api"
import { errText } from "./errors"
import type { SongSummary } from "./types"

interface Props {
  projectId: string
  songs: SongSummary[]
  trash: SongSummary[]
  onChanged: () => void
}

/** Songs des Projekts: anlegen, umbenennen, in den Papierkorb, wiederherstellen. */
export function SongList({ projectId, songs, trash, onChanged }: Props) {
  const { t } = useTranslation("tonstudio")
  const [title, setTitle] = useState("")
  const [showTrash, setShowTrash] = useState(false)
  const [error, setError] = useState("")

  async function run(fn: () => Promise<unknown>) {
    setError("")
    try {
      await fn()
      onChanged()
    } catch (e) {
      setError(errText(e))
    }
  }

  async function rename(id: string, old: string) {
    const next = prompt(t("song_rename"), old)?.trim()
    if (!next || next === old) return
    await run(async () => {
      const song = await tonstudioApi.getSong(projectId, id)
      await tonstudioApi.saveSong(projectId, { ...song, title: next })
    })
  }

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-200">🎼 {t("songs")}</h3>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) run(() => tonstudioApi.createSong(projectId, title.trim())).then(() => setTitle(""))
        }}
      >
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("song_title_placeholder")}
          maxLength={200}
          className="flex-1 rounded bg-slate-900 border border-slate-700 px-2 py-1 text-sm text-slate-200"
        />
        <button type="submit" disabled={!title.trim()} className="rounded bg-violet-600 px-3 py-1 text-sm text-white disabled:opacity-40">
          {t("song_new")}
        </button>
      </form>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {songs.length === 0 && <p className="text-xs text-slate-500">{t("songs_empty")}</p>}
      <ul className="flex flex-col gap-1">
        {songs.map((s) => (
          <li key={s.id} className="group flex items-center gap-2 rounded border border-slate-700 bg-slate-800/50 px-2 py-1.5">
            <span className="flex-1 truncate text-sm text-slate-200">{s.title}</span>
            <span className="text-[11px] text-slate-500">
              {[s.bpm ? `${s.bpm} BPM` : "", s.key ?? "", t("song_tracks", { count: s.tracks })].filter(Boolean).join(" · ")}
            </span>
            <button onClick={() => rename(s.id, s.title)} title={t("song_rename")} className="text-xs text-slate-500 hover:text-slate-200">✏️</button>
            <button
              onClick={() => confirm(t("song_trash_confirm", { title: s.title })) && run(() => tonstudioApi.trashSong(projectId, s.id))}
              title={t("song_trash")}
              className="text-xs text-slate-500 hover:text-red-400"
            >
              🗑️
            </button>
          </li>
        ))}
      </ul>
      {trash.length > 0 && (
        <button onClick={() => setShowTrash((v) => !v)} className="self-start text-xs text-slate-400 hover:text-slate-200">
          {t("trash_toggle", { count: trash.length })}
        </button>
      )}
      {showTrash && (
        <ul className="flex flex-col gap-1">
          {trash.map((s) => (
            <li key={s.id} className="flex items-center gap-2 rounded border border-dashed border-slate-700 px-2 py-1 text-xs text-slate-400">
              <span className="flex-1 truncate">{s.title}</span>
              <button onClick={() => run(() => tonstudioApi.restoreSong(projectId, s.id))} className="hover:text-slate-200">
                ↩️ {t("song_restore")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
