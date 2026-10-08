# HydraHive2 module hub

> 🇩🇪 [Deutsche Version](README.de.md)

First-party module hub for [HydraHive2](https://github.com/hydrahive/hydrahive2.0).

Each top-level directory is an installable module. `hub.json` is the hub
index that the HydraHive backend uses to list, pull and install these
modules. The catalog currently contains **21 entries: 20 end-user
modules plus one developer example template**.

## Installation

A module is installed through the HydraHive backend's module manager
(`Admin Cockpit → Modules`), which:

- pulls the module from this repository or any additional `HH_MODULE_HUB_GIT_URLS`;
- copies the backend into `HH_DATA_DIR/modules/<id>` and the frontend
  into `frontend/src/modules/<id>` in the core checkout;
- runs declared module migrations;
- rebuilds the React frontend and requests a backend restart.

Module backend code is loaded as part of the HydraHive process. Module
frontend code is compiled into the main application. Uninstall removes
the module files but deliberately leaves module database tables and data
in place. The required Tasks module is bundled in the core repository
and is repaired from the bundled source when missing.

## Catalog

The catalog is read at runtime from `hub.json`. The table below lists
the current manifest versions, dependencies, declared summary and
verified contributions. Verified contributions are taken from the
generated `frontend/src/modules/index.generated.ts` after a build that
loads each module's `frontend/index.tsx`.

| Module | Manifest | Depends on | Verified contributions | Summary |
|---|---:|---|---|---|
| **Archiver** | 2.0.2 | — | router, migration | Archives web pages, forum threads and documents in a durable, searchable form. |
| **Atelier** | 1.6.5 | `videoeditor` | router, frontend routes, nav, i18n, `slotBlocks`, `mediaWorkflows` | AI media workshop for images, video, music and short films, project-bound with consistent characters. |
| **Blueprint** | 1.0.2 | — | router, migration | Visual node canvas for conveying layout and flow ideas to an agent non-verbally. |
| **Brettspiele** | 1.0.2 | — | router, migration, `buddyWidgets` | Classic board games such as chess, playable against an agent, with stored results. |
| **Cryptoboard** | 1.1.2 | — | router, migration, agent tools, Butler types, poll jobs | Live crypto dashboard with charts, watchlist, portfolio, trades, alerts and indicators. |
| **Deep Research** | 1.0.2 | — | router, migration, `research_report` tool | Multi-step, source-backed web research that produces a cited report. |
| **Haushaltsbuch** | 1.5.3 | — | router, migration | Local household ledger with bank import, automatic categorisation and an experimental read-only Lidl Plus receipt sync. |
| **Home Assistant** | 1.0.2 | — | router, migration, 4 tools | Connects Home Assistant: list/read entities, render templates and call services. |
| **Mediacenter** | 0.8.1 | — | router, migration, 5 tools, queue/history | Treasure Maps search with media profiles, idempotent SABnzbd hand-off and per-user queue/history. |
| **Mining** | 0.7.2 | — | router, device router, migration, poll job, frontend routes, nav, i18n, rig client, agent tools, skill | Manages GPU rigs on the network for Kryptex: live earnings, pair/approve/revoke rigs, benchmark, auto-switch to the most profitable coin, watchdog, power control (PV). |
| **Minigames** | 1.0.2 | — | router, migration, `buddyWidgets` | A collection of small browser games for short breaks. |
| **Musicplayer** | 1.1.1 | — | router, migration, `buddyMediaWidgets` | Project-scoped, role-aware audio library in Buddy's media slot; stores tracks safely under `media/audio` and supports upload, import, streaming, and download. |
| **Notizbuch** | 1.0.2 | — | router, migration | Simple notepad for texts and ideas, available across projects. |
| **Meine Akte** | 1.0.2 | — | router, migration, 2 read tools, `buddyWidgets` | Personal medical record for findings, medications and diagnoses, with structured imports. |
| **Scratchpad** | 1.0.2 | — | router, 2 tools, nav, i18n, routes | Shared notepad between user and agent with separate, non-shared zones. |
| **Storyteller** | 0.16.0 | — | router, frontend routes, nav, i18n, agent tools | Write books and stories (novel, non-fiction, textbook) with chapter navigator, profiles and AI suggestions. Books are Markdown/JSON files in the project folder, version check against silent overwrites, real AI via HydraHive models with a per-book model picker. Ghostwriter “write scene”: the AI writes a whole scene from its summary, profiles and memory, streamed live, applied only after you accept; “chapter/book” writes many scenes in the background (outline from an idea, progress, cancel, existing text becomes a suggestion); “interview” asks you questions per chapter, you answer by typing or dictating, and the chapter is written in your voice; “in chat” lets the project agent read the book and leave scene text, a scene's title, summary and point of view, new and changed profiles, or new chapters as a proposal you accept or discard – in a chat window right next to the editor (long scenes are read in sections, a proposal much shorter than the scene shows a warning; the project cockpit no longer jumps into the book chat); origin per scene and AI share are shown. “New book” can create a project of its own with a writing team: an author for the chat (no shell, files or git) and seven helpers (plausibility, research, editor, critic, creative, structure, profiles), all on the book's model; helpers file findings and research notes (with sources) that show up in the “Team” tab with a marker in the navigator; buttons in that tab send one helper without a chat (check scene, line edit, critical read, check structure, update profiles) with a cost estimate first, a stop button and the actual cost afterwards; an optional cost limit per job (input + output tokens) applies to background runs, single scenes and team jobs – above it a job only starts after “start anyway”, a team job stops between two rounds and keeps its cost; nothing gets lost: a proposal that replaces another one says so (“replaces a proposal by the editor”), replaced and discarded proposals are listed under “earlier proposals” and can be brought back, deleted scenes return to their old place and deleted books back to the list from the trash; a book that lives in a normal project can be moved to a project of its own with a team (a backup stays in the old project's trash); needs the permission “storyteller.create_project” (admins only by default). Needs core with prose editor (TipTap). |
| **Aufgaben** | 1.0.1 | — | router, migration, 4 tools, `buddyWidgets`, `workspaceTabs` | Persistent task management that survives chat sessions. The agent can create, update and complete tasks. |
| **Video-Editor** | 0.1.2 | — | router, frontend routes, nav, i18n | Web video editor with timeline, filmstrip preview and hybrid export. |
| **Voice** | 0.8.0 | — | router, frontend routes, nav | Voicebox for the HydraHive voice assistant (HA Voice PE) with voice, volume and wake-word settings. |
| **VoIP** | 0.4.3 | — | authenticated registration + incoming-call probe routes, typed gateway contract + fake, frontend routes, nav, i18n | Installable foundation with secret-safe FRITZ!Box registration and a NAT-aware controlled incoming-call test; persistent connections are not enabled yet. |
| **OpenTor OSINT** | 0.1.0 | — | router, migration, 4 read-only tools, frontend routes, nav | Controlled Tor-based OSINT and threat-intelligence research, disabled by default. |
| **AI-Sicherheit** | 0.1.0 | — | router, migration, polling job | Authenticated adapter for local AI-Infra-Guard infrastructure scans; no privileged scanner service is installed automatically. |
| **Beispiel-Modul** | 1.0.1 | — | router, migration | Minimal example module used as a template for new modules. |

Versions, summaries and the "Verified contributions" column are taken
from the module manifests and the current `frontend/index.tsx` exports.
The hub is updated independently of the HydraHive core repository; the
installed version on a given HydraHive host can be different until the
administrator runs an update.

## Authoring a new module

The repository convention for a new module `foo` is:

```text
foo/
├── manifest.json    # id, name, version, depends, summary, ...
├── backend/
│   ├── __init__.py  # register_routes, register_tools, run_migrations
│   └── ...
├── frontend/
│   ├── index.tsx    # exports routes, nav, i18n, optional buddyWidgets,
│   │                # workspaceTabs, slotBlocks, mediaSources, mediaWorkflows
│   └── ...
└── migrations/      # SQL or Python migrations applied at install/update
```

The `example` module is a deliberately small working reference.
HydraHive's module manager copies the module into `HH_DATA_DIR/modules/<id>`
at install time and copies `frontend/` into `frontend/src/modules/<id>`
in the core source tree before rebuilding the application.

Manifest version bumps are required for visible changes; the
`spec-guard` CI workflow in the core repository blocks module updates
that do not change the manifest version.

## Safety and trust

A module's backend code executes inside the HydraHive process. A
module's frontend is compiled into the main application. HydraHive does
not sandbox module Python code. Administrators should only install
modules they have reviewed or originate from a trusted source.

## Documentation language convention

See [I18N.md](I18N.md) for the English/German mirror convention.

## License and contribution

Each module is part of the HydraHive project. Module code is under the
same license as the core project unless a module-specific license is
declared. Bug reports and pull requests are welcome in this repository.
