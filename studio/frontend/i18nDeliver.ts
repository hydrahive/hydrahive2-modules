/** Texte für den Reiter „Ausgabe“ (4d). Ohne Terminal- oder Datei-Hinweise. */
export const deliver_de = {
  deliver_empty: "Die Zeitleiste ist noch leer. Leg im Reiter „Schneiden“ zuerst Clips an – zum Beispiel mit „Aus dem Drehbuch übernehmen“.",
  deliver_summary: "Film: {{length}} min · {{clips}} Clips · {{width}}×{{height}} (Format des Drehbuchs)",
  deliver_placeholders_one: "{{count}} Clip hat noch kein Bild oder Video und erscheint als schwarze Karte mit seinem Namen.",
  deliver_placeholders_other: "{{count}} Clips haben noch kein Bild oder Video und erscheinen als schwarze Karten mit ihrem Namen.",
  deliver_hint: "Der Film entsteht auf dem Server, das kostet nichts. Videos behalten ihren Ton, Musik und Sprache von den Tonspuren werden dazugemischt.",
  deliver_run: "Film als MP4 erzeugen",
  deliver_running: "Film wird erzeugt … {{percent}} %",
  deliver_films: "Fertige Filme",
  deliver_none: "Noch kein Film erzeugt.",
  deliver_film_info: "{{length}} min · {{width}}×{{height}}",
  deliver_missing_one: "{{count}} Medium fehlte beim Erzeugen: ein Bild als schwarze Karte, ein Ton als Stille.",
  deliver_missing_other: "{{count}} Medien fehlten beim Erzeugen: Bilder als schwarze Karten, Ton als Stille.",
  deliver_download: "Herunterladen",
  notice_render_started: "Film wird erzeugt.",
  deliver_err: {
    studio_render_empty: "Die Zeitleiste ist leer – es gibt nichts auszugeben.",
    studio_render_running: "Es wird schon ein Film erzeugt. Bitte warten, bis er fertig ist.",
  },
}

export const deliver_en: typeof deliver_de = {
  deliver_empty: "The timeline is still empty. First add clips in the “Edit” tab – for example with “Take over from the screenplay”.",
  deliver_summary: "Film: {{length}} min · {{clips}} clips · {{width}}×{{height}} (format of the screenplay)",
  deliver_placeholders_one: "{{count}} clip has no image or video yet and appears as a black card with its name.",
  deliver_placeholders_other: "{{count}} clips have no image or video yet and appear as black cards with their names.",
  deliver_hint: "The film is created on the server, at no cost. Videos keep their sound, music and voice from the sound tracks are mixed in.",
  deliver_run: "Create film as MP4",
  deliver_running: "Creating film … {{percent}} %",
  deliver_films: "Finished films",
  deliver_none: "No film created yet.",
  deliver_film_info: "{{length}} min · {{width}}×{{height}}",
  deliver_missing_one: "{{count}} medium was missing while creating: an image as a black card, a sound as silence.",
  deliver_missing_other: "{{count}} media were missing while creating: images as black cards, sound as silence.",
  deliver_download: "Download",
  notice_render_started: "Creating film.",
  deliver_err: {
    studio_render_empty: "The timeline is empty – there is nothing to export.",
    studio_render_running: "A film is already being created. Please wait until it is done.",
  },
}
