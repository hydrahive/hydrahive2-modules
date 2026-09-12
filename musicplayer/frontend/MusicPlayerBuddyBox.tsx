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
        <p className="rounded-[4px] border border-dashed border-[#2a364b] bg-[#0d1420] px-3 py-4 text-center text-[11px] text-[#8d9ab0]">
          {t("mp_select_project")}
        </p>
      </MusicPlayerPanel>
    )
  }

  return <MusicPlayerProjectView key={projectId} projectId={projectId} />
}
