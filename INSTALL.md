# SmartCastRobotics — 설치 및 실행 가이드

다른 PC 에서 처음 clone 후 모든 서비스를 띄우는 절차.

## 1. 사전 요구사항

| 항목 | 권장 버전 | 용도 |
|------|----------|------|
| Python | 3.11 (backend) / 3.12 (PyQt) | 가상환경 분리 |
| Node.js | 20+ | Next.js (ui/web) |
| PostgreSQL 클라이언트 | libpq | psycopg 빌드 (`brew install libpq` on macOS) |
| AWS RDS 인증서 | global-bundle.pem | `sslmode=verify-full` 용 (https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem) |
| Git | any | clone |

## 2. 저장소 가져오기

```bash
git clone https://github.com/Daye-Lee18/SmartCastRobotics_team2.git
cd SmartCastRobotics_team2
```

## 3. Backend (`server/main_service/`) — FastAPI :8000 + Management gRPC :50051

### 3.1 가상환경 + 의존성

```bash
cd server/main_service
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 환경변수 (`.env.local`)

```bash
cp .env.example .env.local
```

`.env.local` 을 열어 실제 값으로 교체:

```
DATABASE_URL="postgresql+psycopg://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/Casting?sslmode=verify-full&sslrootcert=/absolute/path/to/global-bundle.pem"
SMARTCAST_SCHEMA=public
```

**비밀번호와 RDS 엔드포인트는 팀장에게 별도로 받아주세요.** (보안상 git 에 절대 커밋 금지 — `.gitignore` 가 차단)

### 3.3 실행

```bash
PYTHONPATH=src uvicorn main_service.app.main:app --host 0.0.0.0 --port 8000 --env-file .env.local --reload
```

확인: `curl http://localhost:8000/api/dashboard/stats` → 200 응답

### 3.4 (선택) Management gRPC 서버

```bash
PYTHONPATH=src python -m main_service.management.server
# :50051 LISTEN
```

## 4. PyQt Monitoring (`ui/pyqt/factory_operator/`) — 데스크톱 앱

```bash
cd ui/pyqt/factory_operator
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m factory_operator.main
```

`API_BASE_URL` 환경변수로 백엔드 주소 변경 가능 (기본: `http://localhost:8000`).
fallback 모드: `CASTING_DATA_MODE=fallback` (백엔드 미기동 시 mock 데이터 사용).

## 5. Web (`ui/web/`) — Next.js :3001

```bash
cd ui/web
npm install
npm run dev -- --port 3001
```

브라우저: http://localhost:3001

`NEXT_PUBLIC_API_BASE_URL` 등 백엔드 주소 환경변수가 필요하면 `.env.local` 작성 (프로젝트 자체 default 가 `http://localhost:8000`).

## 6. 통합 동작 확인

| 서비스 | 확인 |
|--------|------|
| FastAPI | `curl http://localhost:8000/api/orders` → 200, JSON 배열 |
| PyQt | 데스크톱 창 표시 + 실시간 운영 모니터링 페이지 발주 목록 |
| Web | http://localhost:3001 admin 대시보드 정상 |

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `psycopg.OperationalError: connection refused` | DATABASE_URL 또는 RDS 인증서 경로 오류 | `.env.local` 의 `sslrootcert=` 절대 경로 확인 |
| `psycopg.errors.UndefinedTable` | 잘못된 스키마 | `SMARTCAST_SCHEMA=public` 명시 |
| PyQt 가 백엔드 응답 못함 | 포트/방화벽 | `lsof -i :8000` 으로 LISTEN 확인 |
| Next.js dev 가 다른 포트 점유 | 좀비 프로세스 | `lsof -i :3001` → `kill <PID>` 후 재시작 |
| `ModuleNotFoundError: main_service` | PYTHONPATH 미지정 | 명령 앞에 `PYTHONPATH=src` 추가 |

## 8. 운영 메모

- 활성 DB: **AWS RDS Casting** (public schema, ~33 테이블)
- 임포트 직후 sample 9 파일은 `server/main_service/src/main_service/_examples/` 보존
- e2e 검증 스크립트: `server/main_service/scripts/e2e/` (e2e_pipeline.py / e2e_ord40.py)
