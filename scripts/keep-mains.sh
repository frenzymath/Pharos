#!/bin/bash
# Resume a main agent when its tmux pane reports "Goal stalled".
#
#   tmux new-session -d -s pharos-keep-mains "scripts/keep-mains.sh"
# Log: runtime/logs/keep-mains.log (one line per scan).
INTERVAL=${PHAROS_KEEP_MAINS_INTERVAL:-120}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG="$ROOT/runtime/logs/keep-mains.log"
mkdir -p "$(dirname "$LOG")"
while :; do
  line="$(date '+%F %T')"
  for pdir in "$ROOT"/runtime/projects/*/; do
    p=$(basename "$pdir")
    tag=$(jq -r '.tag // empty' "$pdir/project.json" 2>/dev/null)
    sess="pharos-v3-${tag:-$p}"
    if ! tmux has-session -t "$sess" 2>/dev/null; then line="$line $p:no-session"; continue; fi
    if tmux capture-pane -pt "$sess" -S -12 | grep -q 'Goal stalled'; then
      tmux send-keys -t "$sess" "/goal resume"; sleep 1; tmux send-keys -t "$sess" Enter
      line="$line $p:RESUMED"
    else
      line="$line $p:ok"
    fi
  done
  echo "$line" >> "$LOG"
  sleep "$INTERVAL"
done
