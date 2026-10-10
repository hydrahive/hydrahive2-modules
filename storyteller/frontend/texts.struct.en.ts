// C2 – author may restructure the outline (spec autor-gliederung-c2.md §2b).
import type { StructTexts } from "./texts.struct.de"

export const structEn: StructTexts = {
  struct_switch: "Author may change the outline directly (otherwise as a proposal)",
  struct_switch_help: "Off: adding, deleting, moving and renaming chapters/scenes come from the author as a restructuring proposal you accept. On: the author changes things directly – deleted items go to the trash. Helpers only ever propose.",
  struct_proposal_title: "Proposal from the author: restructure the outline",
  struct_proposal_steps: "Steps",
  struct_proposal_before: "Before",
  struct_proposal_after: "After",
  struct_proposal_new: "new",
  struct_proposal_gone: "removed",
  struct_proposal_replaced: "Replaces an earlier restructuring proposal by {{who}}.",
  struct_apply: "Accept",
  struct_reject: "Discard",
  struct_proposal_hint: "The author proposed restructuring the outline – review and accept it under “Chapter/Book”.",
  struct_reloaded: "The author changed the outline – reloaded.",
  ai_err_chapter_empty: "A chapter would end up empty – the proposal no longer fits the outline.",
  ai_err_after_invalid: "An insertion point no longer exists – the proposal no longer fits the outline.",
  ai_err_steps_invalid: "The proposal is incomplete.",
  ai_err_op_invalid: "The proposal contains an unknown step.",
  ai_err_title_invalid: "A title in the proposal is empty or too long.",
  ai_err_scenes_invalid: "A new chapter in the proposal has no scene.",
  ai_err_job_active: "A team job is working on this book right now – please wait or cancel it.",
  ai_err_scene_not_found: "A scene from the proposal no longer exists – the proposal no longer fits the outline.",
  ai_err_chapter_not_found: "A chapter from the proposal no longer exists – the proposal no longer fits the outline.",
  ai_err_last_chapter: "The last chapter of a book stays.",
}
