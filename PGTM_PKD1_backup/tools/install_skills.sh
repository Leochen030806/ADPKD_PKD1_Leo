#!/usr/bin/env bash
# Install the 5 PGT-M skills into Claude Code (~/.claude/skills), or zip them for claude.ai upload.
#   ./install_skills.sh          -> copy to ~/.claude/skills/
#   ./install_skills.sh --zip    -> write dist/<skill>.zip for Settings -> Skills upload
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS=(pgtm-str-panel-design pgtm-str-panel-order pgtm-ce-report-slides pgtm-gel-titration-report str-csv-allele-report)
if [[ "${1:-}" == "--zip" ]]; then
  mkdir -p "$HERE/dist"
  for s in "${SKILLS[@]}"; do (cd "$HERE/skills" && rm -f "$HERE/dist/$s.zip" && zip -qr "$HERE/dist/$s.zip" "$s"); echo "dist/$s.zip"; done
else
  DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"; mkdir -p "$DEST"
  for s in "${SKILLS[@]}"; do rm -rf "$DEST/$s"; cp -r "$HERE/skills/$s" "$DEST/"; echo "installed $DEST/$s"; done
fi
