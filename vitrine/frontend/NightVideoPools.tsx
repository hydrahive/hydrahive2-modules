import { useTranslation } from "react-i18next"
import type { NightSeason, NightVideoPools as Pools, VideoFile } from "./api"

const SEASONS: NightSeason[] = ["spring", "summer", "autumn", "winter"]

export function toggleNightVideo(pools: Pools, season: NightSeason, name: string): Pools {
  const current = pools[season]
  return {
    ...pools,
    [season]: current.includes(name) ? current.filter((video) => video !== name) : [...current, name],
  }
}

export function NightVideoPools({ pools, videos, onChange }: {
  pools: Pools
  videos: VideoFile[]
  onChange: (pools: Pools) => void
}) {
  const { t } = useTranslation("vitrine")
  return (
    <fieldset className="space-y-3 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
      <legend className="px-1 text-xs font-bold text-[#c8d2df]">{t("night_videos_title")}</legend>
      <p className="text-xs text-[#9aa7bc]">{t("night_videos_hint")}</p>
      {SEASONS.map((season) => (
        <div key={season}>
          <p className="mb-1 text-xs font-bold text-[#9aa7bc]">{t(`season.${season}`)}</p>
          {videos.length === 0
            ? <p className="text-xs text-[#5b6b82]">{t("no_videos")}</p>
            : <div className="flex flex-wrap gap-2">
                {videos.map((video) => (
                  <label key={video.name} className="flex items-center gap-1.5 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1 text-xs text-[#c8d2df]">
                    <input
                      type="checkbox"
                      checked={pools[season].includes(video.name)}
                      onChange={() => onChange(toggleNightVideo(pools, season, video.name))}
                    />
                    {video.name}
                  </label>
                ))}
              </div>}
        </div>
      ))}
    </fieldset>
  )
}
