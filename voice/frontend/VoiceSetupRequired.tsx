import { Cable, Mic, Radio, RefreshCw, Wifi } from "lucide-react"

interface VoiceSetupRequiredProps {
  checking: boolean
  onRetry: () => void
  t: (key: string) => string
}

/** Friendly setup state shown while no voice bridge can be reached. */
export function VoiceSetupRequired({ checking, onRetry, t }: VoiceSetupRequiredProps) {
  const steps = [
    {
      icon: <Cable size={18} />,
      title: t("setup_step_flash"),
      text: t("setup_step_flash_hint"),
    },
    {
      icon: <Wifi size={18} />,
      title: t("setup_step_wifi"),
      text: t("setup_step_wifi_hint"),
    },
    {
      icon: <Radio size={18} />,
      title: t("setup_step_pair"),
      text: t("setup_step_pair_hint"),
    },
  ]

  return (
    <main className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-5 sm:p-8">
      <section className="w-full max-w-3xl rounded-[8px] border border-[#1c2636] bg-[#0a0f18] shadow-[0_20px_60px_rgba(0,0,0,.28)]">
        <div className="border-b border-[#1c2636] px-6 py-6 text-center sm:px-10 sm:py-8">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-[#25445a] bg-[#102536] text-[#69d7ff]">
            <Mic size={22} />
          </span>
          <h1 className="mt-4 text-xl font-bold text-[#e8eef8]">{t("setup_title")}</h1>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#8d9ab0]">
            {t("setup_description")}
          </p>
        </div>

        <div className="grid gap-3 p-5 sm:grid-cols-3 sm:p-6">
          {steps.map((step, index) => (
            <div
              key={step.title}
              className="rounded-[6px] border border-[#1c2636] bg-[#0b1119] p-4"
            >
              <div className="flex items-center gap-2 text-[#69d7ff]">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-[#132333]">
                  {step.icon}
                </span>
                <span className="text-[11px] font-bold uppercase tracking-[.12em] text-[#5f7890]">
                  {index + 1}
                </span>
              </div>
              <h2 className="mt-3 text-sm font-bold text-[#dce6f3]">{step.title}</h2>
              <p className="mt-1.5 text-xs leading-5 text-[#7f8da3]">{step.text}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-col items-center justify-between gap-3 border-t border-[#1c2636] px-6 py-4 sm:flex-row">
          <p className="text-center text-xs leading-5 text-[#7f8da3] sm:text-left">
            {t("setup_availability")}
          </p>
          <button
            type="button"
            disabled={checking}
            onClick={onRetry}
            className="flex shrink-0 items-center gap-2 rounded-[5px] border border-[#2b506b] bg-[#12283a] px-3 py-2 text-xs font-semibold text-[#bfe9ff] transition-colors hover:border-[#3a7198] hover:bg-[#173247] disabled:cursor-wait disabled:opacity-60"
          >
            <RefreshCw size={14} className={checking ? "animate-spin" : ""} />
            {t(checking ? "setup_checking" : "setup_retry")}
          </button>
        </div>
      </section>
    </main>
  )
}
