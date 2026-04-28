#!/usr/bin/env bash
# 3 서비스 동시 실행 — tmux 또는 백그라운드 fallback.
#
# tmux 가 설치되어 있으면 새 세션에 3 창을 열어 각 서비스 실시간 출력 확인.
# tmux 없으면 nohup 으로 백그라운드 실행 + logs/ 디렉터리에 출력.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v tmux >/dev/null 2>&1; then
  SESS="smartcast"
  if tmux has-session -t "$SESS" 2>/dev/null; then
    echo "→ 기존 세션 attach: tmux attach -t $SESS  (또는 ./scripts/stop-all.sh 후 재실행)"
    exit 0
  fi
  tmux new-session -d -s "$SESS" -n backend "$ROOT/scripts/run-backend.sh"
  tmux new-window -t "$SESS" -n pyqt    "$ROOT/scripts/run-pyqt.sh"
  tmux new-window -t "$SESS" -n web     "$ROOT/scripts/run-web.sh"
  tmux select-window -t "$SESS:0"
  echo "→ tmux 세션 '$SESS' 시작 (windows: backend / pyqt / web)"
  echo "  attach:  tmux attach -t $SESS"
  echo "  중단:    ./scripts/stop-all.sh"
else
  mkdir -p "$ROOT/logs"
  echo "→ tmux 미설치 — 백그라운드 + logs/*.log 로 출력"
  nohup "$ROOT/scripts/run-backend.sh" > "$ROOT/logs/backend.log" 2>&1 &
  echo "  backend  PID=$!"
  nohup "$ROOT/scripts/run-pyqt.sh"    > "$ROOT/logs/pyqt.log"    2>&1 &
  echo "  pyqt     PID=$!"
  nohup "$ROOT/scripts/run-web.sh"     > "$ROOT/logs/web.log"     2>&1 &
  echo "  web      PID=$!"
  echo "  로그:    tail -f logs/{backend,pyqt,web}.log"
  echo "  중단:    ./scripts/stop-all.sh"
fi
