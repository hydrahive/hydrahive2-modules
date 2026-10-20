#!/bin/bash
# Archify als feste Kopie ins Modul holen (nie automatisch; Spec §5). Aufruf: scripts/vendor-archify.sh <tag-oder-commit>
# Danach: Tests laufen lassen, VENDOR.md prüfen, Modul-Version anheben, PR.
set -euo pipefail
REF="${1:?Tag oder Commit angeben, z. B. v3.2.0}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone -q https://github.com/tt-a1i/archify.git "$TMP/src"
git -C "$TMP/src" checkout -q "$REF"
COMMIT="$(git -C "$TMP/src" rev-parse HEAD)"
VERSION="$(python3 -c "import json;print(json.load(open('$TMP/src/archify/package.json'))['version'])")"
rm -rf "$HERE/vendor/archify.new"; mkdir -p "$HERE/vendor/archify.new"
# Nur was zum Laufen nötig ist: keine fertig gebauten Beispielseiten (*.html, ~13 MB), keine node_modules, keine
# Paket-Sperrdatei. Die Beispiel-Vorlagen (JSON/Markdown) bleiben – Archify prüft sie beim Start, Agenten lernen daran.
tar -C "$TMP/src/archify" --exclude=node_modules --exclude=package-lock.json --exclude='examples/*.html' \
  --exclude='examples/**/*.html' -cf - . | tar -C "$HERE/vendor/archify.new" -xf -
rm -rf "$HERE/vendor/archify"; mv "$HERE/vendor/archify.new" "$HERE/vendor/archify"
cat > "$HERE/vendor/VENDOR.md" <<EOT
# Fremdcode im Modul Diagramme

| Teil | Herkunft | Version | Commit | Lizenz |
|---|---|---|---|---|
| \`vendor/archify/\` | https://github.com/tt-a1i/archify (Ordner \`archify/\`) | $VERSION | \`$COMMIT\` | MIT (\`vendor/archify/LICENSE\`) |

Weggelassen: fertig gebaute Beispielseiten (\`examples/**/*.html\`), \`node_modules/\`, \`package-lock.json\`. Unverändert übernommen, keine eigenen Änderungen.
Erneuern nur gezielt mit \`scripts/vendor-archify.sh <tag>\` (Spec §5), nie automatisch.
EOT
echo "Archify $VERSION ($COMMIT) übernommen."
