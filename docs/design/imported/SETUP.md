# 설치 가이드 — 다른 PC 에서 프론트엔드 + 백엔드 실행

> 이 문서는 개발 환경 기준입니다. 프로덕션 배포는 [docs/DEPLOY-phase-a-to-c3.md](DEPLOY-phase-a-to-c3.md) 참조.
>
> 본 가이드는 **Next.js + FastAPI Interface Service** 설치까지 다룹니다. 추가 컴포넌트:
> - **Management Service (gRPC :50051)**: PyQt 실시간 스트림/생산 시작에 필수 → [README.md §4](../README.md#4-백엔드--management-service-grpc-50051)
> - **PyQt 관제 모니터링**: Factory Operator PC → [README.md §5](../README.md#5-pyqt-관제-모니터링-factory-operator-pc)
> - **Jetson Orin NX**: 이미지 publishing + ESP32 Serial relay → [jetson_publisher/README.md](../jetson_publisher/README.md)

## 사전 요구 사항

### 필수

| 소프트웨어 | 버전 | 설치 방법 | 확인 명령 |
|---|---|---|---|
| **Node.js** | 20 이상 (v23 권장) | https://nodejs.org 또는 `brew install node` | `node -v` |
| **npm** | 10 이상 | Node.js 에 포함 | `npm -v` |
| **Python** | **3.12 권장** (3.11+ 허용, macOS Apple Silicon 에서 PyQt5/grpcio 는 3.14 휠 없음) | https://python.org 또는 `brew install python@3.12` | `python3.12 --version` |
| **Git** | 2.x | OS 기본 설치 또는 https://git-scm.com | `git --version` |
| **Tailscale** | 최신 | https://tailscale.com/download | `tailscale status` |

### 선택 (DB GUI)

| 소프트웨어 | 설치 |
|---|---|
| **DBeaver Community** | `brew install --cask dbeaver-community` (Mac) 또는 https://dbeaver.io/download |

---

## Step 1: Tailscale 로그인

DB 서버 (`100.107.120.14`) 는 Tailscale VPN 네트워크에 있습니다. 접근하려면 같은 Tailscale 계정에 연결되어야 합니다.

```bash
# Tailscale 설치 후
tailscale up

# 로그인 성공 확인
tailscale status

# DB 서버 접근 확인
ping -c 2 100.107.120.14
```

`ping` 이 응답하면 Tailscale 연결 성공.

---

## Step 2: 소스 코드 클론

```bash
git clone https://github.com/kiminbean/casting-factory.git
cd casting-factory
```

---

## Step 3: 프론트엔드 설치

```bash
# 프로젝트 루트 디렉터리에서 실행 (casting-factory/)
cd casting-factory
npm install
```

### 환경 변수 (`.env.local`)

프로젝트 루트에 `.env.local` 파일 생성:

```bash
cat > .env.local << 'EOF'
# 관리자 비밀번호 (클라이언트 사이드 단순 게이트)
NEXT_PUBLIC_ADMIN_PASSWORD=admin1234
EOF
```

> *.env.local* 은 `.gitignore` 에 의해 git 추적에서 제외됩니다.

### 프론트엔드 실행

```bash
npm run dev
```

**접속**: http://localhost:3000

LAN 에서 다른 기기로 접근하려면 `http://<내IP>:3000` 으로 접속 가능 (`next dev -H 0.0.0.0` 이 기본 설정).

> **주의**: `next.config.ts` 의 `allowedDevOrigins` 에 자신의 IP 대역이 포함되어야 LAN 에서 JS 리소스가 차단되지 않습니다. 현재 `192.168.0.*` 이 설정되어 있으며, 다른 대역에서 접근 시 추가 필요:
>
> ```ts
> // next.config.ts
> allowedDevOrigins: ["192.168.0.*", "10.0.0.*", "localhost"],
> ```

---

## Step 4: 백엔드 설치 (별도 터미널)

```bash
# 프로젝트 루트에서 backend/ 디렉터리로 이동
cd casting-factory/backend

# Python 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate      # macOS/Linux
# Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 환경 변수 (`backend/.env.local`)

`backend/` 디렉터리 안에 `.env.local` 파일 생성:

```bash
cat > .env.local << 'EOF'
# PostgreSQL 원격 DB 서버 (Tailscale VPN)
# 비밀번호는 프로젝트 관리자에게 문의하세요.
# search_path 는 smartcast v2 스키마 우선 탐색을 위해 권장.
DATABASE_URL=postgresql+psycopg://team2:<비밀번호>@100.107.120.14:5432/smartcast_robotics?options=-c%20search_path%3Dsmartcast%2Cpublic
EOF
```

**`<비밀번호>` 를 실제 값으로 교체**해야 합니다. 비밀번호는 프로젝트 관리자(kisoo)에게 문의하세요.

> *.env.local* 은 `.gitignore` 에 의해 git 추적에서 제외됩니다. **절대 비밀번호를 git 에 커밋하지 마세요.**

> **DB 정책 (2026-04-14 이후)**: PostgreSQL 16 + TimescaleDB **단독**. SQLite 폴백은 backend 코드에서 완전 제거되었습니다. `DATABASE_URL` 미설정 시 fail-fast. smartcast v2 스키마(27 테이블, Confluence 32342045 v59) + `public` 스키마의 legacy 3개 테이블(alerts, handoff_acks, transport_tasks, rfid_scan_log) 혼용.

### 백엔드 실행

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**접속**: http://localhost:8000

### 동작 확인

```bash
# 헬스체크
curl http://localhost:8000/health

# 주문 목록 (JSON)
curl http://localhost:8000/api/orders | python3 -m json.tool | head -20

# 제품 마스터
curl http://localhost:8000/api/products | python3 -m json.tool
```

---

## Step 5: 동작 확인

프론트엔드와 백엔드를 모두 실행한 상태에서:

| URL | 기대 결과 |
|---|---|
| http://localhost:3000/ | SmartCast Robotics 랜딩 (3 버튼) |
| http://localhost:3000/admin/login | 관리자 비밀번호 입력 (admin1234) |
| http://localhost:3000/admin | 관리자 허브 (주문 관리 + 품질 관리 카드) |
| http://localhost:3000/orders | 주문 관리 (탭: 전체/접수/승인/생산/생산 완료/출고/완료) |
| http://localhost:3000/customer | 고객 발주 포털 (4단계 폼) |
| http://localhost:3000/customer/lookup | 이메일로 주문 조회 |
| http://localhost:8000/health | `{"status": "ok"}` |
| http://localhost:8000/api/orders | JSON 주문 목록 (12+ 건) |

---

## DB 접속 (DBeaver)

원격 PostgreSQL 에 직접 접속하여 데이터를 확인/편집할 수 있습니다.

### DBeaver 설치

```bash
# macOS
brew install --cask dbeaver-community

# Windows
# https://dbeaver.io/download 에서 Community Edition 다운로드

# Linux
sudo snap install dbeaver-ce
```

### 연결 정보

| 필드 | 값 |
|---|---|
| Connection Type | PostgreSQL |
| Server Host | `100.107.120.14` |
| Port | `5432` |
| Database | `smartcast_robotics` |
| Username | `team2` |
| Password | 관리자에게 문의 |

**절차**: DBeaver 좌상단 🔌 아이콘 → PostgreSQL → 위 정보 입력 → **Test Connection** → 드라이버 자동 다운로드 → **Finish**

### 유용한 쿼리

```sql
-- 주문 목록 (최신순)
SELECT id, status, customer_name, company_name, total_amount, created_at
FROM orders ORDER BY created_at DESC;

-- 상태별 집계
SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status;

-- 제품 카탈로그
SELECT id, name, category, base_price, load_class_range FROM products;

-- 하중 등급 (EN 124)
SELECT code, load_tons, use_case FROM load_classes ORDER BY display_order;

-- 제품 × 하중 JOIN
SELECT p.id, p.name, p.load_class_range,
       lc_min.load_tons AS min_tons, lc_max.load_tons AS max_tons
FROM products p
LEFT JOIN load_classes lc_min ON lc_min.code = split_part(p.load_class_range, ' ~ ', 1)
LEFT JOIN load_classes lc_max ON lc_max.code = split_part(p.load_class_range, ' ~ ', 2);
```

---

## 프로젝트 구조 요약

```
casting-factory/
├── src/                        # Next.js 16 프론트엔드
│   ├── app/
│   │   ├── page.tsx            # 공개 랜딩 (SmartCast Robotics)
│   │   ├── admin/login/        # 관리자 비밀번호 입력
│   │   ├── admin/              # 관리자 허브
│   │   ├── orders/             # 주문 관리 (탭, 상세, 액션 버튼)
│   │   ├── quality/            # 품질 관리
│   │   └── customer/           # 고객 포털 (발주, 조회)
│   ├── components/             # SmartCastLogo, Header, AdminShell, FactoryMap 등
│   └── lib/                    # api.ts, types.ts, utils.ts
│
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py             # FastAPI 앱 + lifespan + 라우터 등록
│   │   ├── database.py         # SQLAlchemy engine + .env.local 로더
│   │   ├── models/models.py    # ORM 17개 테이블 (Order, Product, LoadClass 등)
│   │   ├── schemas/schemas.py  # Pydantic v2 스키마
│   │   ├── routes/             # orders, production, quality, logistics, alerts, schedule, websocket
│   │   └── seed.py             # 초기 시드 데이터 (idempotent)
│   ├── scripts/                # DB 마이그레이션 SQL
│   ├── requirements.txt        # Python 의존성
│   └── .env.local              # DATABASE_URL (gitignored)
│
├── monitoring/                 # PyQt5 관제 모니터링 앱 (선택)
├── firmware/                   # ESP32 컨베이어 컨트롤러 (선택)
├── docs/                       # 프로젝트 문서
│   ├── SETUP.md                # ← 이 문서
│   └── CONFLUENCE_FACTS.md     # Confluence 팩트 수집본
├── .env.local                  # NEXT_PUBLIC_ADMIN_PASSWORD (gitignored)
├── next.config.ts              # Next.js 설정 (allowedDevOrigins, rewrites)
└── README.md                   # 프로젝트 개요
```

---

## 환경 변수 정리

### 프론트엔드 (프로젝트 루트 `.env.local`)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_ADMIN_PASSWORD` | `admin1234` | 관리자 비밀번호 (클라이언트 게이트, 진짜 인증 아님) |
| `NEXT_PUBLIC_API_URL` | (빈 문자열) | API 서버 URL. 빈 값이면 Next.js rewrites 가 localhost:8000 으로 프록시 |

### 백엔드 (`backend/.env.local`)

| 변수 | 예시 | 설명 |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://team2:<pw>@100.107.120.14:5432/smartcast_robotics?options=-c%20search_path%3Dsmartcast%2Cpublic` | PostgreSQL 접속 문자열. **미설정 시 fail-fast** (SQLite 폴백 제거됨) |
| `INTERFACE_PROXY_START_PRODUCTION` | `0` | 1 이면 `/api/production/start` 를 Management gRPC proxy 로 라우팅 (SPEC-C2). 모듈 import 시점 고정 — flip 시 uvicorn 전체 재시작 필요 |
| `MANAGEMENT_GRPC_HOST` / `PORT` | `localhost` / `50051` | Management Service(gRPC) 엔드포인트 |

> Management Service(`:50051`) · PyQt monitoring · Jetson publisher 환경변수는 [README.md](../README.md#8-환경변수-요약) 및 [docs/DEPLOY-phase-a-to-c3.md](DEPLOY-phase-a-to-c3.md) 참조.

---

## 트러블슈팅

### 프론트엔드가 빈 화면

- **백엔드가 실행 중인지 확인**: `curl http://localhost:8000/health`
- 백엔드가 꺼져 있으면 Next.js rewrites 가 실패 → API 호출 전부 에러

### "connection refused" (백엔드)

- **Tailscale 연결 확인**: `tailscale status` → `100.107.120.14` 가 보여야 함
- **DB 비밀번호 확인**: `backend/.env.local` 의 `DATABASE_URL` 비밀번호가 정확한지
- **포트 확인**: `nc -zv 100.107.120.14 5432` → "succeeded" 여야 함

### LAN 에서 접속 시 JS 리소스 차단

- `next.config.ts` 의 `allowedDevOrigins` 에 자신의 IP 대역 추가
- 예: `"10.0.0.*"`, `"172.16.*.*"` 등

### DBeaver 접속 실패

- Tailscale 연결 확인 (위와 동일)
- DBeaver 에서 PostgreSQL JDBC 드라이버 자동 다운로드 허용 여부 확인
- Host `100.107.120.14`, Port `5432`, DB `smartcast_robotics`, User `team2` 재확인

### "Application startup failed" (백엔드)

- `backend/.env.local` 의 `DATABASE_URL` 확인
- 원격 DB 스키마가 최신인지 확인 (shipped_at 컬럼 누락 등)
- `tail -50 /tmp/uvicorn.log` 로 상세 에러 확인

---

## 주의 사항

1. **비밀번호를 절대 git 에 커밋하지 마세요**. `.env.local` 은 `.gitignore` 에 포함되어 있지만, 실수로 `.env` 같은 다른 이름을 쓰면 커밋될 수 있습니다.

2. **DB 는 공유 자원**입니다. 원격 `smartcast_robotics` DB 에 여러 사람이 동시에 접속합니다. 데이터를 함부로 DELETE 하지 마세요.

3. **관리자 비밀번호 (`admin1234`) 는 진짜 인증이 아닙니다**. `NEXT_PUBLIC_*` 환경 변수는 브라우저 번들에 포함되어 DevTools 에서 확인 가능합니다. 실 운영 전 Auth0/Clerk/JWT 등 진짜 인증 시스템 도입이 필요합니다.

4. **`next.config.ts` 의 rewrites** 가 `/api/*` 요청을 `http://localhost:8000/api/*` 로 프록시합니다. 프론트엔드와 백엔드를 **같은 PC 에서 실행**해야 프록시가 동작합니다. 만약 백엔드를 다른 PC 에서 실행한다면 `NEXT_PUBLIC_API_URL=http://<백엔드IP>:8000` 환경변수를 설정해야 합니다.

---

## 연락처

- **프로젝트 관리자**: kisoo (kiminbean@gmail.com)
- **GitHub**: https://github.com/kiminbean/casting-factory
- **DB 비밀번호 문의**: 프로젝트 관리자에게 직접 연락
