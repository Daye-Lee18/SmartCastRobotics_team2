# E2E — Jetson → Management → AI Server 이미지 플로우

목표: 로컬 Mac 웹캠으로 Jetson publisher 를 시뮬레이션하고, IP 단계 진입 시 AI Server 에 이미지가 업로드되는지 확인.

## 구성

```
[Mac FaceTime 캠]    [Management Server]   [AI Server (Tailscale)]
 publisher.py ──gRPC──> :50051 ──SSH──────> 100.66.177.119
                      (image_sink)           /home/team2/datasets/inspection/
                      (image_forwarder)
```

## 사전 조건

1. `backend/.env.local` 에 `MGMT_AI_HOST/USER/PASS` 설정 완료 (`MGMT_AI_PASS` 는 환경변수)
2. AI Server 접속 검증 완료 (`AIUploader.health_check() == True`)
3. PostgreSQL(100.107.120.14) 접근 가능, `items` 테이블에 진행중 항목 존재
4. 웹캠 연결 (`/dev/video0` 또는 FaceTime HD 카메라)

## 스텝

### 1) Management Server 기동

```bash
cd backend/management
source venv/bin/activate
set -a && source ../.env.local && set +a
export MGMT_IMAGE_SPOOL_DIR=/tmp/casting-image-spool
export MGMT_IMAGE_BATCH_SEC=10           # E2E 확인용 짧게
export MGMT_IP_CAMERA_ID=CAM-INSP-MAC
python server.py
# 로그: "image_forwarder 활성: spool=... batch=10.0s"
```

### 2) Publisher 실행 (로컬 Mac 웹캠)

별도 터미널:
```bash
cd jetson_publisher
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt opencv-python

export MANAGEMENT_GRPC_HOST=127.0.0.1
export MANAGEMENT_GRPC_PORT=50051
export JETSON_CAMERA_ID=CAM-INSP-MAC
export JETSON_CAMERA_INDEX=0
export JETSON_FPS=2
python3 publisher.py
# 로그: "connecting 127.0.0.1:50051 (insecure)" "camera 0 opened 1280x720"
```

### 3) IP 진입 시뮬 (DB 직접 업데이트)

```bash
psql "$DATABASE_URL" <<'EOF'
-- 현재 QUE 상태 item 1건을 IP 로 전이
WITH t AS (
  SELECT item_id FROM items WHERE cur_stage = 'PP' ORDER BY item_id LIMIT 1
)
UPDATE items
SET cur_stage = 'IP', mfg_at = NOW()
WHERE item_id IN (SELECT item_id FROM t)
RETURNING item_id, cur_stage;
EOF
```

또는 기존 Production UI/gRPC 로 공정 진행.

### 4) Server 로그 확인

```
INFO services.image_forwarder: snapshot ok: CAM-INSP-MAC_IP_item123_...jpg (48921 bytes)
INFO services.image_forwarder: flush ok: 1 uploaded     # 10초 내
```

### 5) AI Server 측 확인

```bash
ssh team2@100.66.177.119 \
  "ls -la /home/team2/datasets/inspection/CAM-INSP-MAC/$(date +%Y-%m-%d)/ | tail"
```

파일이 보이면 E2E 성공.

### 6) 수동 flush (디버깅)

로컬 스풀 확인:
```bash
ls -la /tmp/casting-image-spool/
```

`*.jpg` + `*.json` 쌍이 쌓여 있다가 10초마다 사라져야 함 (AI Server 로 이동).

## 정리

```bash
# publisher 종료: Ctrl+C
# server 종료: Ctrl+C
# 남은 스풀 정리
rm -rf /tmp/casting-image-spool
```

## 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `snapshot skipped: 최신 프레임 없음` | publisher 미연결 또는 카메라 ID 불일치 | `MGMT_IP_CAMERA_ID` == `JETSON_CAMERA_ID` 확인 |
| `image_forwarder 비활성` | AI env 미로드 | `source backend/.env.local` |
| `upload failed ... Timeout` | Tailscale 단절 | `ping 100.66.177.119` 복구 후 재시도 (스풀에 파일 보존됨) |
| `Cannot open camera index 0` | macOS 권한 | 시스템 설정 → 프라이버시 → 카메라 → 터미널 허용 |
| SLA 알람 폭주 | items.mfg_at 과거 시각 | `UPDATE items SET mfg_at=NOW()` + Monitor 재기동 |

## Jetson 실배포 버전

위 2) 단계를 Jetson 에서 실행:
```bash
bash jetson_publisher/deploy.sh --install      # 최초 1회
ssh jetson@100.77.62.67 "nano ~/casting-image-publisher/env"   # MANAGEMENT_GRPC_HOST 수정
ssh jetson@100.77.62.67 "sudo systemctl start casting-image-publisher"
ssh jetson@100.77.62.67 "sudo journalctl -u casting-image-publisher -f"
```
