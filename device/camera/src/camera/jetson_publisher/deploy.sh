#!/usr/bin/env bash
# Jetson Image Publisher — 로컬 Mac → Jetson Orin NX 배포 스크립트
#
# 사전 요구:
#   backend/.env.local 에 MGMT_JETSON_HOST, MGMT_JETSON_USER, MGMT_JETSON_PASS 설정
#   sshpass 설치 (`brew install hudochenkov/sshpass/sshpass`) — 평문 비밀번호 사용 시
#
# 사용:
#   bash jetson_publisher/deploy.sh
#   bash jetson_publisher/deploy.sh --install   # 최초 systemd 유닛 설치까지
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# env 로드
set -a
# shellcheck disable=SC1091
source "$REPO_ROOT/backend/.env.local"
set +a

: "${MGMT_JETSON_HOST:?MGMT_JETSON_HOST missing}"
: "${MGMT_JETSON_USER:?MGMT_JETSON_USER missing}"

SSH_OPTS="-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null"
REMOTE_DIR="/home/${MGMT_JETSON_USER}/casting-image-publisher"

if [[ -n "${MGMT_JETSON_SSH_KEY:-}" ]]; then
  SSH_CMD=(ssh $SSH_OPTS -i "$MGMT_JETSON_SSH_KEY")
  RSYNC_SSH="ssh $SSH_OPTS -i $MGMT_JETSON_SSH_KEY"
elif [[ -n "${MGMT_JETSON_PASS:-}" ]]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "ERROR: sshpass 필요 — 'brew install hudochenkov/sshpass/sshpass' 또는 SSH 키 사용" >&2
    exit 2
  fi
  SSH_CMD=(sshpass -p "$MGMT_JETSON_PASS" ssh $SSH_OPTS)
  RSYNC_SSH="sshpass -p $MGMT_JETSON_PASS ssh $SSH_OPTS"
else
  echo "ERROR: MGMT_JETSON_PASS 또는 MGMT_JETSON_SSH_KEY 중 하나 필요" >&2
  exit 2
fi

TARGET="${MGMT_JETSON_USER}@${MGMT_JETSON_HOST}"
echo ">>> target: $TARGET:$REMOTE_DIR"

"${SSH_CMD[@]}" "$TARGET" "mkdir -p $REMOTE_DIR/generated"

# rsync 코드 (venv/cache 제외)
rsync -avz --delete \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='deploy.sh' \
  -e "$RSYNC_SSH" \
  "$SCRIPT_DIR/" "$TARGET:$REMOTE_DIR/"

# 최초 설치 옵션
if [[ "${1:-}" == "--install" ]]; then
  echo ">>> installing systemd unit (sudo on remote)"
  "${SSH_CMD[@]}" "$TARGET" bash <<'EOF'
set -e
cd ~/casting-image-publisher
# env 파일이 없으면 example 로 초기화
if [[ ! -f env ]]; then
  cp env.example env
  echo ">>> created ~/casting-image-publisher/env (fill MANAGEMENT_GRPC_HOST 등)"
fi
# 의존성
if ! python3 -c "import grpc" 2>/dev/null; then
  pip3 install --user -r requirements.txt
fi
if ! python3 -c "import cv2" 2>/dev/null; then
  echo ">>> installing python3-opencv (apt)"
  sudo apt-get update && sudo apt-get install -y python3-opencv
fi
# systemd 유닛 등록
sudo cp systemd/casting-image-publisher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable casting-image-publisher.service
echo ">>> installed. Start with: sudo systemctl start casting-image-publisher"
EOF
else
  echo ">>> code synced. 서비스 재시작: ssh $TARGET 'sudo systemctl restart casting-image-publisher'"
fi
