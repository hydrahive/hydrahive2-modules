/** G1 Schritt 1 „Idee“ mit echten Daten: Formular, Karten, Ersetzen- und Lösch-Dialog. */
import { useTranslation } from "react-i18next"
import { DeleteDialog } from "../DeleteDialog"
import { cardsOf } from "./guidedLogic"
import { IdeaCards } from "./IdeaCards"
import { IdeaForm } from "./IdeaForm"
import { ReplaceDialog } from "./ReplaceDialog"
import { StepHead } from "./ui"
import type { GuidedState } from "./useGuided"

export function StepIdeaLive({ g }: { g: GuidedState }) {
  const { t } = useTranslation("studio")
  const cards = cardsOf(g.plan)
  return (
    <div>
      <StepHead n={1} title={t("guided.step.1.title")} text={t("guided.idea_head")} />
      <IdeaForm idea={g.idea} kind={g.kind} length={g.length} format={g.plan?.screenplay.aspect_ratio ?? "16:9"} hasScenes={cards.length > 0}
        busy={g.writing} error={g.error} model={g.plan?.screenplay.models.text ?? ""}
        onIdea={g.setIdea} onKind={g.setKind} onLength={g.setLength} onFormat={g.setFormat} onRun={g.startSuggest} onSelf={() => g.addScene()} />
      {cards.length > 0 && (
        <IdeaCards cards={cards} saved={g.saved} busy={g.busy} onText={g.changeText} onMove={g.move}
          onDelete={(id, n) => g.setDeleting({ id, n })} onAdd={() => g.addScene()} />
      )}
      {g.asking && <ReplaceDialog count={cards.length} busy={g.writing} onReplace={() => void g.write(true)} onAppend={() => void g.write(false)}
        onClose={() => g.setAsking(false)} />}
      {g.deleting && <DeleteDialog name={t("guided.scene_n", { n: g.deleting.n })} busy={g.busy} onConfirm={g.confirmDelete} onClose={() => g.setDeleting(null)} />}
    </div>
  )
}
