#!/usr/bin/env bash
# 3 서비스 중단 — 기존 tmux 세션 정리 + 포트별 프로세스 kill.
set -uo pipefail

# 예전 run-all.sh 로 띄운 tmux 세션이 있으면 같이 정리
if command -v tmux >/dev/null 2>&1 && tmux has-session -t smartcast 2>/dev/null; then
  tmux kill-session -t smartcast
  echo "✓ tmux 세션 'smartcast' 종료"
fi

# 포트 점유 프로세스 정리
for PORT in 8000 50051 3001; do
  PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "  port $PORT: PID $PIDS kill"
    kill $PIDS 2>/dev/null || true
  fi
done

# PyQt (포트 없음, 명령으로 추적)
PYQT_PIDS=$(pgrep -f "factory_operator.main" 2>/dev/null || true)
if [ -n "$PYQT_PIDS" ]; then
  echo "  PyQt PID $PYQT_PIDS kill"
  kill $PYQT_PIDS 2>/dev/null || true
fi

echo "✓ 정리 완료"
