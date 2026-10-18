import { AudioLines, Mic, Music, Volume2, VolumeX } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { peakDb } from "./audioGraph"
import { audibleTracks, dbText, GAIN_MAX, GAIN_MIN, type Mixer } from "./mixLogic"
import type { TrackId, TrackMix } from "./timelineApi"

interface Props {
  mixer: Mixer
  counts: Record<TrackId, number>
  playing: boolean
  onTrack: (id: TrackId, v: TrackMix) => void
  onDuck: (on: boolean) => void
}

const CHANNELS: { id: TrackId; key: string; icon: typeof Mic }[] = [
  { id: "V1", key: "mix_original", icon: AudioLines }, { id: "A1", key: "mix_voice", icon: Mic }, { id: "A2", key: "mix_music", icon: Music },
]

/** Reiter „Ton“: Mischpult mit drei Kanälen (Originalton, Sprache, Musik), Pegel beim Abspielen, Ducking-Schalter. */
export function MixerPanel({ mixer, counts, playing, onTrack, onDuck }: Props) {
  const { t } = useTranslation("studio")
  const hears = audibleTracks(mixer.tracks)
  return (
    <section className="flex h-full min-h-0 flex-col gap-2 overflow-y-auto p-3" data-mixer>
      <div className="flex flex-wrap items-center gap-3 text-xs text-[#8d9ab0]">
        <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("mix_title")}</h2>
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-[#c3ccdd]" title={t("mix_duck_hint")}>
          <input type="checkbox" checked={mixer.duck} onChange={(e) => onDuck(e.target.checked)} data-mix-duck className="accent-[#69d7ff]" />
          {t("mix_duck")}
        </label>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5">
        {CHANNELS.map((ch) => <Channel key={ch.id} id={ch.id} label={t(ch.key)} Icon={ch.icon} v={mixer.tracks[ch.id]} count={counts[ch.id]}
          live={hears.has(ch.id)} playing={playing} onChange={(v) => onTrack(ch.id, v)} />)}
      </div>
      <p className="text-[10px] leading-relaxed text-[#68758a]">{t("mix_hint")}</p>
    </section>
  )
}

function Channel({ id, label, Icon, v, count, live, playing, onChange }: {
  id: TrackId; label: string; Icon: typeof Mic; v: TrackMix; count: number; live: boolean; playing: boolean; onChange: (v: TrackMix) => void
}) {
  const { t } = useTranslation("studio")
  const db = v.gain_db ?? 0
  const btn = (on: boolean, color: string) => `rounded-[4px] border px-2 py-0.5 text-[10px] font-black ${on ? color : "border-[#2a364b] text-[#8d9ab0] hover:border-[#46617f]"}`
  return (
    <div className={`flex flex-col gap-1.5 rounded-[6px] border p-2 ${live ? "border-[#2a364b] bg-[#0d1420]" : "border-[#2a364b]/50 bg-[#0d1420]/40 opacity-60"}`}
      data-mix-channel={id} data-mix-live={live ? "1" : undefined}>
      <div className="flex items-center gap-1.5 text-xs font-bold text-[#e8eef8]">
        <Icon size={13} className="shrink-0" /> <span className="truncate">{label}</span>
        <span className="ml-auto text-[10px] font-normal text-[#68758a]">{t("mix_clips", { count })}</span>
      </div>
      <div className="flex items-center gap-2">
        <input type="range" min={GAIN_MIN} max={GAIN_MAX} step={0.5} value={db} aria-label={t("mix_volume_of", { name: label })}
          onChange={(e) => onChange({ gain_db: Number(e.target.value) })} onDoubleClick={() => onChange({ gain_db: 0 })}
          className="min-w-0 flex-1 accent-[#69d7ff]" data-mix-gain={id} />
        <span className="w-16 shrink-0 text-right font-mono text-[11px] text-[#e8eef8]" data-mix-db={id}>{dbText(db)}</span>
      </div>
      <Meter id={id} playing={playing && live} />
      <div className="flex gap-1.5">
        <button type="button" aria-pressed={!!v.mute} onClick={() => onChange({ mute: !v.mute })} className={btn(!!v.mute, "border-[#ff6b8a] bg-[#ff6b8a]/15 text-[#ff6b8a]")}
          data-mix-mute={id}>{v.mute ? <VolumeX size={11} className="mr-1 inline" /> : <Volume2 size={11} className="mr-1 inline" />}{t("mix_mute")}</button>
        <button type="button" aria-pressed={!!v.solo} onClick={() => onChange({ solo: !v.solo })} className={btn(!!v.solo, "border-[#ffb86b] bg-[#ffb86b]/15 text-[#ffb86b]")}
          data-mix-solo={id}>{t("mix_solo")}</button>
      </div>
    </div>
  )
}

/** Pegelanzeige: liest beim Abspielen den Analyser des Kanals (−60 … 0 dB), sonst leer. */
function Meter({ id, playing }: { id: TrackId; playing: boolean }) {
  const [level, setLevel] = useState(0)
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => {
      const db = peakDb(id)
      setLevel(db === null || db === -Infinity ? 0 : Math.max(0, Math.min(1, (db + 60) / 60)))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); setLevel(0) }
  }, [id, playing])
  return (
    <div className="relative h-1.5 overflow-hidden rounded-[2px] bg-[#111827]" data-mix-meter={id} aria-hidden>
      <span className="absolute inset-y-0 left-0 bg-gradient-to-r from-[#2a7f62] via-[#e6c35c] to-[#ff6b8a]" style={{ width: `${Math.round(level * 100)}%` }} />
    </div>
  )
}
