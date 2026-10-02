// Reine Entscheidung „Musik nach dem Video fortsetzen?“ (ohne React, testbar).
// Till 02.10.2026, Variante B: nur wenn die Musik vor dem Video lief.

export interface ResumeState { resume: boolean }
export interface VideoMoment { videoPaused: boolean; pointerDown: boolean; seeking: boolean }

/** Video startet: merken, ob Musik lief. Ein zweites Video hält das Gemerkte. */
export function onVideoStart(state: ResumeState, musicPlaying: boolean): ResumeState {
  return { resume: state.resume || musicPlaying }
}

/** Nach kurzer Wartezeit: fortsetzen nur, wenn das Video steht, nichts gedrückt ist und
 *  nicht gespult wird (die eingebaute Zeitleiste meldet der Seite nur „seeking“). */
export function shouldResume(state: ResumeState, moment: VideoMoment): boolean {
  return state.resume && moment.videoPaused && !moment.pointerDown && !moment.seeking
}

/** Nutzer bedient die Musik selbst: nichts mehr automatisch tun. */
export function forget(): ResumeState {
  return { resume: false }
}
