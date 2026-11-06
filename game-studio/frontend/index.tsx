import { GameStudioPage } from "./GameStudioPage"

export const routes = [{ path: "/game-studio", element: <GameStudioPage /> }]
export const nav = [
  { path: "/game-studio", icon: "Gamepad2", labelKey: "gameStudio", group: "working", area: "medien", roles: [] },
]

export const i18n = {
  de: {
    gameStudio: {
      title: "Game Studio",
      loading: "Game Studio wird geladen",
      landing: {
        title: "Vom Spieleinfall zum belegten, spielbaren Prototyp",
        subtitle: "Plane einen kleinen Spielkern, verbinde später deine Workstation und entscheide anhand echter Läufe statt Versprechen.",
        chooseStart: "Wie möchtest du anfangen?",
      },
      entry: {
        new: { title: "Neues Spiel", description: "Forme eine Idee zu einem kleinen, klar abgegrenzten Vertical Slice." },
        adopt: { title: "Projekt übernehmen", description: "Erfasse ein bestehendes Godot- oder Unreal-Projekt, ohne vorhandene Arbeit zu überschreiben." },
        archive: { title: "Archiv untersuchen", description: "Prüfe ein altes Projekt zunächst sicher und statisch, bevor etwas verändert wird." },
        open: "Öffnen",
      },
      drafts: {
        title: "Meine Spielprojekte", new: "Neues Projekt", emptyTitle: "Noch kein Spielprojekt",
        emptyText: "Wähle oben einen Einstieg. Das Projekt wird im Workspace angelegt und über Samba freigegeben.",
        step: "Schritt {{step}} von 5",
      },
      engine: { godot: "Godot", unreal: "Unreal Engine", unity: "Unity" },
      sharing: {
        title: "Samba-Workspace",
        user: "Freigabe-Benutzer",
        available: "Samba ist bereit. Neue Projekte werden als eigene Workspace-Freigabe angelegt.",
        unavailable: "Samba ist noch nicht betriebsbereit. Neue Projekte können erst danach angelegt werden.",
      },
      workstation: {
        title: "Workstation und sichere Ausführung",
        core_update_required: "Der HydraHive-Core muss aktualisiert werden, bevor eine Game-Workstation erkannt werden kann.",
        not_connected: "Noch keine Workstation verbunden. Planung und Entwürfe funktionieren trotzdem.",
        offline: "Eine Workstation ist bekannt, aber derzeit nicht erreichbar.",
        approval_required: "Die Workstation ist erreichbar, ihre Isolation wurde aber noch nicht administrativ freigegeben.",
        ready_for_binding: "Die sichere Workstation-Grundlage ist bereit. Ein Projekt kann später daran gebunden werden.",
        runnerPending: "Build und Test bleiben gesperrt, bis PR4 den echten isolierten Godot-Runner liefert.",
      },
      flow: {
        navigation: "Schritte zum ersten Vertical Slice", back: "Zurück zur Übersicht", untitled: "Neuer Spielentwurf",
        stepCount: "Schritt {{step}} von 5", saveFailed: "Der Entwurf konnte nicht gespeichert werden.",
        saving: "Speichert…", continue: "Speichern und weiter", briefEmpty: "Beschreibe zuerst deine Spielidee.",
        runnerLockedTitle: "Bauen und Testen ist noch nicht freigeschaltet",
        runnerLockedGodot: "Das Projekt liegt im Samba-Workspace. Der automatische Godot-Lauf folgt mit dem isolierten Runner aus PR4.",
        runnerLockedExternal: "Das Projekt liegt im Samba-Workspace und kann mit {{engine}} geöffnet werden. Ein automatischer sicherer Runner ist dafür noch nicht freigegeben.",
        runnerSafety: "Kein Host-Fallback und keine vorgetäuschten Ergebnisse.", buildDisabled: "Build starten · folgt mit PR4",
        steps: { idea: "Idee", brief: "Game Brief", slice: "Spielkern", run: "Bauen", evidence: "Ergebnis" },
        intro: {
          new: "Beginne klein: eine Kernaktion, ein klares Ziel und ein sichtbares Ergebnis.",
          adopt: "Beschreibe, was bereits existiert und was auf keinen Fall überschrieben werden darf.",
          archive: "Beschreibe Herkunft und Ziel des Archivs. Eine echte Dateiprüfung folgt mit dem sicheren Runner.",
        },
        panels: {
          "1": { title: "Was soll entstehen?", description: "Gib dem Vorhaben einen Namen und beschreibe die Idee in deinen Worten." },
          "2": { title: "Der kurze Game Brief", description: "Lege Genre und Zielplattform fest. Der Umfang bleibt bewusst klein." },
          "3": { title: "Der kleinste spielbare Kern", description: "Definiere genau eine Kernaktion und woran du erkennst, dass sie funktioniert." },
          "4": { title: "Sicher bauen und starten", description: "Dieser Schritt wird erst aktiv, wenn der echte isolierte Runner verfügbar ist." },
          "5": { title: "Ansehen und entscheiden", description: "Später erscheinen hier Screenshot, Laufbericht und deine Abnahmeentscheidung." },
        },
      },
      fields: {
        engine: "Engine für dieses Projekt",
        title: "Arbeitstitel", titlePlaceholder: "z. B. Leuchtturm im Sturm", idea: "Deine Spielidee",
        ideaPlaceholder: {
          new: "Was tut der Spieler, und welches Gefühl soll entstehen?",
          adopt: "Was ist bereits vorhanden, und wobei soll Game Studio helfen?",
          archive: "Woher stammt das Archiv, und was möchtest du daraus retten?",
        },
        genre: "Genre", genrePlaceholder: "z. B. Puzzle-Abenteuer", platform: "Zielplattform",
        coreAction: "Eine Kernaktion", success: "Sichtbares Erfolgskriterium",
      },
      platform: { desktop: "Desktop", web: "Web", mobile: "Mobil" },
      error: { title: "Game Studio konnte nicht geladen werden", text: "Bitte versuche es erneut. Es werden keine Demo-Daten angezeigt.", retry: "Erneut laden" },
    },
  },
  en: {
    gameStudio: {
      title: "Game Studio",
      loading: "Loading Game Studio",
      landing: {
        title: "From a game idea to a proven playable prototype",
        subtitle: "Plan a small playable core, connect your workstation later, and decide from real runs instead of promises.",
        chooseStart: "How would you like to start?",
      },
      entry: {
        new: { title: "New game", description: "Turn an idea into a small and clearly scoped vertical slice." },
        adopt: { title: "Adopt a project", description: "Capture an existing Godot or Unreal project without overwriting prior work." },
        archive: { title: "Inspect an archive", description: "Inspect an old project safely and statically before changing anything." },
        open: "Open",
      },
      drafts: {
        title: "My game projects", new: "New project", emptyTitle: "No game project yet",
        emptyText: "Choose a starting point. The project is created in its workspace and shared through Samba.", step: "Step {{step}} of 5",
      },
      engine: { godot: "Godot", unreal: "Unreal Engine", unity: "Unity" },
      sharing: {
        title: "Samba workspace",
        user: "Share user",
        available: "Samba is ready. New projects receive their own workspace share.",
        unavailable: "Samba is not ready yet. New projects can only be created after it is available.",
      },
      workstation: {
        title: "Workstation and safe execution", core_update_required: "Update HydraHive Core before a game workstation can be detected.",
        not_connected: "No workstation is connected yet. Planning and drafts still work.",
        offline: "A workstation is known but currently offline.",
        approval_required: "The workstation is online, but its isolation has not been approved by an administrator.",
        ready_for_binding: "The safe workstation foundation is ready. A project can be bound later.",
        runnerPending: "Build and test stay locked until PR4 provides the real isolated Godot runner.",
      },
      flow: {
        navigation: "Steps to the first vertical slice", back: "Back to overview", untitled: "New game draft",
        stepCount: "Step {{step}} of 5", saveFailed: "The draft could not be saved.", saving: "Saving…", continue: "Save and continue",
        briefEmpty: "Describe your game idea first.", runnerLockedTitle: "Build and test are not available yet",
        runnerLockedGodot: "The project is in its Samba workspace. Automated Godot runs follow with the isolated runner in PR4.",
        runnerLockedExternal: "The project is in its Samba workspace and can be opened with {{engine}}. An automated safe runner is not approved for it yet.",
        runnerSafety: "No host fallback and no fabricated results.", buildDisabled: "Start build · follows with PR4",
        steps: { idea: "Idea", brief: "Game brief", slice: "Playable core", run: "Build", evidence: "Result" },
        intro: {
          new: "Start small: one core action, one clear goal, and one visible result.",
          adopt: "Describe what exists and what must never be overwritten.",
          archive: "Describe the archive's origin and your goal. Safe file inspection follows with the runner.",
        },
        panels: {
          "1": { title: "What should be created?", description: "Name the effort and describe the idea in your own words." },
          "2": { title: "The short game brief", description: "Choose genre and target platform while keeping the scope small." },
          "3": { title: "The smallest playable core", description: "Define one core action and the visible proof that it works." },
          "4": { title: "Build and run safely", description: "This step activates only when the real isolated runner is available." },
          "5": { title: "Review and decide", description: "A screenshot, run report, and acceptance decision will appear here later." },
        },
      },
      fields: {
        engine: "Engine for this project",
        title: "Working title", titlePlaceholder: "e.g. Lighthouse in the storm", idea: "Your game idea",
        ideaPlaceholder: { new: "What does the player do, and how should it feel?", adopt: "What exists, and how should Game Studio help?", archive: "Where is the archive from, and what should be recovered?" },
        genre: "Genre", genrePlaceholder: "e.g. puzzle adventure", platform: "Target platform",
        coreAction: "One core action", success: "Visible success criterion",
      },
      platform: { desktop: "Desktop", web: "Web", mobile: "Mobile" },
      error: { title: "Game Studio could not be loaded", text: "Please try again. No demo data will be shown.", retry: "Try again" },
    },
  },
}
