#!/usr/bin/env bash
# 4 서비스 동시 실행 — GUI 터미널 4개 또는 백그라운드 fallback.
#
# GUI 터미널이 있으면 backend / management / pyqt / web 을 각각 별도 창으로 실행.
# GUI 터미널을 열 수 없으면 nohup 으로 백그라운드 실행 + logs/ 디렉터리에 출력.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

open_terminal() {
  local title="$1"
  local command="$2"
  local hold_command
  printf -v hold_command 'cd %q; %s; status=$?; echo; echo "[%s] exited with status ${status}"; read -r -p "Press Enter to close..."' "$ROOT" "$command" "$title"

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -lc "$hold_command" >/dev/null 2>&1 &
  elif command -v konsole >/dev/null 2>&1; then
    konsole --new-tab --title "$title" -e bash -lc "$hold_command" >/dev/null 2>&1 &
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$title" --command="bash -lc $(printf '%q' "$hold_command")" >/dev/null 2>&1 &
  elif command -v mate-terminal >/dev/null 2>&1; then
    mate-terminal --title="$title" -- bash -lc "$hold_command" >/dev/null 2>&1 &
  elif command -v lxterminal >/dev/null 2>&1; then
    lxterminal --title="$title" -e bash -lc "$hold_command" >/dev/null 2>&1 &
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$hold_command" >/dev/null 2>&1 &
  else
    return 1
  fi
}

if open_terminal "smartcast-backend" "$ROOT/scripts/run-backend.sh"; then
  open_terminal "smartcast-management" "$ROOT/scripts/run-management.sh"
  open_terminal "smartcast-pyqt" "$ROOT/scripts/run-pyqt.sh"
  open_terminal "smartcast-web" "$ROOT/scripts/run-web.sh"
  echo "→ GUI 터미널 창 4개 시작 (backend / management / pyqt / web)"
  echo "  중단:    ./scripts/stop-all.sh"
else
  mkdir -p "$ROOT/logs"
  echo "→ GUI 터미널 없음 — 백그라운드 + logs/*.log 로 출력"
  nohup "$ROOT/scripts/run-backend.sh" > "$ROOT/logs/backend.log" 2>&1 &
  echo "  backend  PID=$!"
  nohup "$ROOT/scripts/run-management.sh" > "$ROOT/logs/management.log" 2>&1 &
  echo "  management PID=$!"
  nohup "$ROOT/scripts/run-pyqt.sh"    > "$ROOT/logs/pyqt.log"    2>&1 &
  echo "  pyqt     PID=$!"
  nohup "$ROOT/scripts/run-web.sh"     > "$ROOT/logs/web.log"     2>&1 &
  echo "  web      PID=$!"
  echo "  로그:    tail -f logs/{backend,management,pyqt,web}.log"
  echo "  중단:    ./scripts/stop-all.sh"
fi
