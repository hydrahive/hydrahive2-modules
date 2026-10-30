// Musicplayer-Slot: bindet den Player strikt an das aktive Projekt.
import { useTranslation } from "react-i18next"
import { MusicPlayerPanel } from "./MusicPlayerPanel"
import { MusicPlayerProjectView } from "./MusicPlayerProjectView"

export function MusicPlayerBuddyBox({ projectId }: {
  projectId?: string | null
  onPrompt?: (text: string) => void
}) {
  const { t } = useTranslation("musicplayer")

  if (!projectId) {
    return (
      <MusicPlayerPanel title={t("mp_title")} trackCount={0}>
        <p className="rounded-[4px] border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-4 text-center text-[11px] text-[#9aa7bc]">
          {t("mp_select_project")}
        </p>
      </MusicPlayerPanel>
    )
  }

  return <MusicPlayerProjectView key={projectId} projectId={projectId} />
}
