#!/usr/bin/env bash
# Ship the built courtroom app to the SAS instance's nginx web root (MOO-226).
# Run from the repo root on the dev machine after `cd courtroom && npm run build`:
#
#   bash deploy/push_site_to_sas.sh root@<public-ip>
#
# Uses rsync over ssh (falls back to scp if rsync is missing on either side).
set -euo pipefail

TARGET="${1:?usage: push_site_to_sas.sh root@<public-ip>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/courtroom/dist"
DEST="/opt/split-decision-site"

[ -f "$DIST/index.html" ] || { echo "courtroom/dist missing — run: cd courtroom && npm run build" >&2; exit 1; }

if command -v rsync >/dev/null 2>&1 && ssh "$TARGET" 'command -v rsync' >/dev/null 2>&1; then
  rsync -az --delete --info=progress2 "$DIST/" "$TARGET:$DEST/"
else
  ssh "$TARGET" "mkdir -p $DEST"
  scp -r "$DIST/." "$TARGET:$DEST/"
fi

echo "shipped. verify: curl -sI http://${TARGET#*@}/ | head -3"
