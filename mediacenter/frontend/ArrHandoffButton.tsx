import { Check, Loader2, Send } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { errorCode, errorMessage, mediacenterApi } from "./api"
import type { ArrTargets, MediaType, ModuleStatus, SearchResult } from "./types"

/** Radarr kennt Filme, Sonarr Serien — alles andere geht direkt an SABnzbd. */
const SERVICE_BY_MEDIA: Partial<Record<MediaType, "radarr" | "sonarr">> = {
  movie: "radarr", tv: "sonarr",
}

export function serviceFor(mediaType: MediaType): "radarr" | "sonarr" | undefined {
  return SERVICE_BY_MEDIA[mediaType]
}

interface Props {
  release: SearchResult
  status: ModuleStatus | null
}

/**
 * Übergibt einen Treffer an Radarr/Sonarr statt direkt an SABnzbd.
 *
 * Der Zieldienst übernimmt Download, Umbenennung und Import — er kennt die
 * Bibliothek. Das vermeidet auch, dass ein Direktdownload in einer Kategorie
 * landet, die Radarr überwacht, ohne dass Radarr ihn bestellt hat.
 *
 * Ist der Titel dort noch nicht angelegt, fragt die Komponente Qualitätsprofil
 * und Ordner ab — geraten wird nichts.
 */
export function ArrHandoffButton({ release, status }: Props) {
  const { t } = useTranslation("mediacenter")
  const service = serviceFor(release.media_type)
  const configured = service === "radarr" ? status?.radarr_configured : status?.sonarr_configured

  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [targets, setTargets] = useState<ArrTargets | null>(null)
  const [profile, setProfile] = useState<number | null>(null)
  const [folder, setFolder] = useState<string>("")

  // Ohne Dienst, ohne Konfiguration oder ohne freigegebene Fassung: kein Knopf.
  if (!service || !configured) return null
  if (release.decision !== "eligible" || !release.result_id) return null

  const send = async (withTargets: boolean) => {
    setBusy(true)
    setError(null)
    try {
      const response = await mediacenterApi.arrHandoff({
        result_id: release.result_id as string,
        service,
        ...(withTargets && profile ? { quality_profile_id: profile } : {}),
        ...(withTargets && folder ? { root_folder_path: folder } : {}),
      })
      setDone(response.added ? t("arr.addedAndSent") : t("arr.sent"))
      setTargets(null)
    } catch (cause) {
      // Der Titel ist dort noch nicht angelegt — Auswahl nachfordern.
      // Über den Rohcode, nicht über den übersetzten Text (der ändert sich).
      if (errorCode(cause) === "arr_target_required") {
        await loadTargets()
      } else {
        setError(errorMessage(cause))
      }
    } finally {
      setBusy(false)
    }
  }

  const loadTargets = async () => {
    try {
      const loaded = await mediacenterApi.arrTargets(service)
      setTargets(loaded)
      setProfile(loaded.quality_profiles.at(-1)?.id ?? null)
      setFolder(loaded.root_folders[0]?.path ?? "")
    } catch (cause) {
      setError(errorMessage(cause))
    }
  }

  if (done) return <span className="flex shrink-0 items-center gap-1.5 text-xs font-bold text-emerald-300">
    <Check size={14} />{done}
  </span>

  return <div className="flex shrink-0 flex-col items-stretch gap-2">
    {!targets && <button type="button" onClick={() => void send(false)} disabled={busy}
      className="flex items-center justify-center gap-2 rounded-[4px] border border-violet-400/50 bg-violet-400/15 px-3 py-2 text-xs font-bold text-violet-100 transition hover:bg-violet-400/25 disabled:cursor-not-allowed disabled:opacity-50">
      {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
      {t("arr.handoff", { service: service === "radarr" ? "Radarr" : "Sonarr" })}
    </button>}

    {targets && <div className="w-full max-w-xs space-y-2 rounded-[6px] border border-violet-400/30 bg-violet-400/[6%] p-2.5">
      <p className="text-[11px] text-[#a9b6c9]">{t("arr.newTitleHint")}</p>
      <label className="block text-[10px] font-bold uppercase tracking-wider text-[#8d9ab0]">
        {t("arr.qualityProfile")}
        <select value={profile ?? ""} onChange={(event) => setProfile(Number(event.target.value))}
          className="mt-1 w-full rounded-[4px] border border-[#30405a] bg-[#0c121d] px-2 py-1.5 text-xs font-normal text-[#e8eef8]">
          {targets.quality_profiles.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
        </select>
      </label>
      <label className="block text-[10px] font-bold uppercase tracking-wider text-[#8d9ab0]">
        {t("arr.rootFolder")}
        <select value={folder} onChange={(event) => setFolder(event.target.value)}
          className="mt-1 w-full rounded-[4px] border border-[#30405a] bg-[#0c121d] px-2 py-1.5 text-xs font-normal text-[#e8eef8]">
          {targets.root_folders.map((entry) => <option key={entry.path} value={entry.path}>{entry.path}</option>)}
        </select>
      </label>
      <div className="flex gap-2">
        <button type="button" onClick={() => setTargets(null)}
          className="flex-1 rounded-[4px] border border-[#34445d] px-2 py-1.5 text-xs font-bold text-[#8d9ab0] hover:text-[#d4deeb]">
          {t("cancel", { defaultValue: "Abbrechen" })}
        </button>
        <button type="button" onClick={() => void send(true)} disabled={busy || !profile || !folder}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-[4px] bg-violet-400/25 px-2 py-1.5 text-xs font-bold text-violet-100 ring-1 ring-violet-400/50 disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          {t("arr.addAndSend")}
        </button>
      </div>
    </div>}

    {error && <p className="max-w-xs text-[11px] text-rose-300" role="alert">{error}</p>}
  </div>
}
