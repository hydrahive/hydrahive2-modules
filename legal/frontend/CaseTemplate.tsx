import type { AgentTemplateInfo } from "./api"

/** Statt der Modellwahl: Der Rechts-Agent nutzt das Agenten-Template (Kern). Ändern nur Admins auf der LLM-Seite. */
export function CaseTemplate({ info }: { info: AgentTemplateInfo }) {
  return (
    <div className="space-y-0.5 text-xs">
      <span className="font-semibold text-[#d7deea]">
        Modell des Rechts-Agenten:{" "}
        <span className="font-mono font-normal text-[#e8eef8]">{info.chain[0] || "–"}</span>
      </span>
      <p className="text-[11px] leading-4 text-[#9aa7bc]">
        Aus dem Template „{info.label}“{info.chain.length > 1 ? `, Ersatz: ${info.chain.slice(1).join(" → ")}` : ""}.
        Ändern kann es ein Admin unter LLM → Agenten-Templates.
      </p>
    </div>
  )
}
