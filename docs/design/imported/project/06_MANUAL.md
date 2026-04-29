# 06. 사용자 매뉴얼

> **버전**: V6 (2026-04-24)
> **대상 독자**: 고객, 관리자(Admin), 공장 운영자(Factory Operator)
> **관련**: [01_PRD.md](./01_PRD.md), [03_PROCESS.md](./03_PROCESS.md)

---

## 1. 사용자 유형별 매뉴얼 개요

| 사용자 | 주 사용 시스템 | 주요 업무 |
|---|---|---|
| **고객 (Customer)** | Next.js 웹 (customer 라우트) | 제품 조회, 주문 제출, 주문 상태 확인 |
| **관리자 (Admin)** | Next.js 웹 (admin 라우트) | 주문 검토/승인, 제품·장비 관리, 분석 |
| **공장 운영자 (Factory Operator)** | PyQt5 데스크톱 | 실시간 모니터링, 생산 시작, AMR/장비 대응 |

---

## 2. 고객 매뉴얼 (Customer)

### 2.1 로그인
1. 접속: https://smartcast-robotics.example (예정) 또는 내부 LAN URL
2. 이메일 + 비밀번호 입력 → 로그인
3. 세션 자동 갱신

### 2.2 주문 흐름 (5단계 이내 완료 원칙)

#### Step 1: 표준 제품 조회
- `카테고리별 필터` 활용 (CMH 원형 / RMH 사각 / EMH 경량)
- 제품 카드: 이미지, 이름, 재질, 기본 가격대, 하중 등급 확인

#### Step 2: 제품 옵션 선택
- 규격: 직경(600~1400mm), 두께(40~80mm)
- 하중 등급: D400 / E600 / F900
- 재질: GC200 / GC250 / GCD500 등
- 후처리 옵션 선택
- 수량 입력
- 희망 납기일 선택
- (선택) 비고란

#### Step 3: 디자인 미리보기
- 선택한 사양에 따른 제품 요약 확인
- 기본 디자인 시안 확인

#### Step 4: 견적 확인
- 자동 계산된 예상 합계 = [제품 기본 단가 + 옵션 가산비] × 수량
- 예상 납기 범위 표시
- "최종 견적은 관리자 검토 후 확정됩니다" 안내 확인

#### Step 5: 주문서 제출
- 필수 입력: 회사명, 연락처, 배송지 주소, 담당자명, 이메일
- 요약 페이지에서 전체 확인
- "제출" 클릭 → 주문 ID 부여

### 2.3 주문 상태 조회
`/customer/orders` 접속.

6단계 상태 확인:
1. **접수 (RCVD)**: 관리자 검토 전
2. **검토 중**: 관리자 검토 진행
3. **승인됨 (APPR)**: 생산 시작 대기
4. **생산 중 (MFG)**: 공장에서 제작 중
5. **출하 준비 (DONE/SHIP)**: 검사 완료, 출고 준비
6. **완료 (COMP)**: 배송 완료

상태 변경 시 등록된 이메일로 알림 발송.

### 2.4 과거 주문 이력
- `내 주문` 페이지에서 제출한 모든 주문 상시 열람
- 상세 옵션 내역 재확인 가능

### 2.5 FAQ
| 질문 | 답 |
|---|---|
| 주문 후 취소할 수 있나요? | RCVD / APPR 단계에서만 가능. MFG 이후는 관리자 문의 |
| 수량을 변경할 수 있나요? | APPR 전까지 관리자에게 수정 요청 |
| 견적이 예상보다 높습니다 | 관리자가 생산 여건에 따라 수정할 수 있음. 수정 요청 상태에서 재검토 |
| 납기가 지연되고 있어요 | 상태를 확인하세요. 필요 시 관리자에게 문의 |

---

## 3. 관리자 매뉴얼 (Admin)

### 3.1 로그인
- 일반 로그인과 동일한 페이지에서 관리자 계정 (role=admin) 로그인
- 로그인 후 자동 `/admin` 리다이렉트

### 3.2 대시보드 (`/admin/dashboard`)
- 오늘의 주문 건수 (RCVD / APPR / MFG / DONE)
- 생산 진행 요약
- 장비 가동률
- 최근 알람

### 3.3 주문 관리 (`/admin/orders`)

#### 주문 검토
1. 주문 리스트에서 선택
2. 상세 사양 확인
3. 생산 가능 여부 판단 (기술적 제약 확인)
4. 예상 견적 수동 수정 가능
5. 예상 납기 확정

#### 승인 / 반려 / 수정 요청
- **승인 (APPR)**: 정상 진행
- **반려 (REJT)**: 생산 불가 사유 명시
- **수정 요청**: 고객에게 옵션 수정 요청

#### 상태 전이 기록
- `ord_log` 테이블에 자동 기록 (prev_stat, new_stat, changed_by=관리자 user_id)

### 3.4 제품 관리
- 신규 제품 카탈로그 등록
- 제품 옵션 (`product_option`) 수정
- 기본 가격 조정
- 이미지 업로드

### 3.5 장비 관리 (`/admin/equipment`)
- 장비 목록 (res_id, res_type, 상태)
- 장비별 작업 내역 (equip_task_txn)
- 에러 로그 (equip_err_log)

### 3.6 분석 리포트 (`/admin/analytics`)
- 리드타임 분포
- 검사 통과율
- AMR 가동률
- 주문별 KPI

### 3.7 주의 사항
- 주문자 정보·연락처는 안전하게 저장됨 (SR-ORD-03 비기능)
- 관리자 액션은 모두 audit log 에 기록됨
- 고객에게 영향을 주는 변경은 알림 자동 발송

---

## 4. 공장 운영자 매뉴얼 (Factory Operator - PyQt)

### 4.1 시작 전 체크리스트
1. Factory Operator PC 부팅
2. Tailscale 연결 확인 (메뉴바 아이콘 초록)
3. DB 접근 가능 여부 (`monitoring/app/management_client.py` 가 gRPC 연결)
4. Management Service 기동 여부 (공장 네트워크 내 `:50051`)
5. Jetson Publisher 기동 여부 (카메라 프리뷰 확인)

### 4.2 PyQt 앱 실행
```bash
cd monitoring
source .venv/bin/activate
python main.py
```

### 4.3 메인 대시보드
- **공정 흐름 뷰**: 주형→주조→냉각→탈형→후처리→검사→출고 단계별 진행 상황
- **AMR 상태판**: 각 AMR의 위치·배터리·현재 태스크
- **장비 상태판**: 각 장비의 cur_stat (IDLE/RUNNING/FAILED)
- **알람 영역**: 실시간 에러/경고

### 4.4 주요 작업

#### 4.4.1 생산 시작 (Start Production)
1. `주문 관리` 탭으로 이동
2. **대기 주문 목록** 확인 (상태 APPR)
3. 시작할 주문 선택 (다중 선택 가능)
4. **"생산 시작" 버튼** 클릭
5. 확인 다이얼로그에서 **YES**
6. 시스템 자동 처리:
   - `ord_stat.ord_stat` = 'APPR' → 'MFG'
   - `ord_log` 에 전이 기록 (changed_by=운영자 user_id)
   - `item` 테이블에 qty만큼 아이템 INSERT
   - TaskManager 가 순차 작업 생성 (주형→주조→...→검사)

#### 4.4.2 AMR 수리 완료 처리
1. `AMR 관리` 탭 또는 메인 대시보드의 AMR 카드
2. **FAILED 상태**의 AMR 확인
3. 물리적 복구 완료 후 **"수리 완료" 버튼** 클릭
4. 시스템 처리:
   - `trans_stat.cur_stat` = 'FAILED' → 'IDLE'
   - FSM 전이 기록
   - AMR 다시 배차 대상에 편입

**2026-04-22 이후 개선**: 수리 완료 버튼은 **항상 표시** (이전: 특정 상태에서만 표시). 독립 버튼으로 분리.

#### 4.4.3 Handoff Button 이벤트 확인
ESP32 물리 버튼은 공장 바닥에서 작업자가 누름. PyQt는 결과만 표시:
- `handoff_acks` 테이블에 이벤트 INSERT
- `transport_tasks.status` = 'handoff_complete'
- AMR FSM: `AT_DESTINATION/UNLOADING` → `UNLOAD_COMPLETED`
- PyQt 대시보드에 알림 배지

**Orphan Handoff** (활성 태스크 없이 버튼이 눌린 경우):
- `handoff_acks.orphan=true`
- 로그만 기록, 실제 FSM 전이 없음
- 알람 영역에 경고 표시

#### 4.4.4 검사 결과 모니터링
- 실시간 `WatchItems` gRPC stream 으로 검사 결과 표시
- 양품: 녹색 체크 표시 + 출고 팔레트 할당
- 불량품: 빨간색 X + 폐기 이송 태스크 자동 생성
- 검사 실패: 노란색 경고 + 운영자 개입 요청

### 4.5 에러 대응

#### AMR 에러
- 알람 영역에 AMR-XX 에러 표시
- 에러 코드 확인 (`trans_err_log`)
- 배터리 부족 (battery_pct < 20%): 자동 충전소 이동
- 경로 막힘: 물리 점검 후 "수리 완료" 버튼

#### 장비 에러
- 알람에 equip-XX 표시
- `equip_err_log.err_msg` 확인
- 해당 장비 담당 정비사 호출
- 복구 후 PyQt에서 상태 업데이트

#### Jetson / 비전 에러
- 카메라 프레임 끊김 감지
- Jetson SSH 접속 (`ssh jetson-conveyor`)
- `journalctl -u image_publisher.service` 로그 확인
- 재시작: `sudo systemctl restart image_publisher.service`

#### Management Service 장애
- PyQt gRPC 연결 실패 알림
- Management PC 확인
- 재시작 후 자동 reconnect

### 4.6 공정 중단 / 재개

#### 긴급 중단
1. 메인 대시보드 상단 **"긴급 중단" 버튼**
2. 확인 후 실행:
   - 모든 진행 중 `MFG` 주문 보류 (`ord_stat.ord_stat`은 그대로 MFG 유지, `pp_task_txn.txn_stat`를 PROC→HOLD로 전환 — HOLD 지원 여부 확인 필요)
   - AMR 현재 위치 정지
   - 컨베이어 STOPPED

#### 재개
1. 원인 해결 후 **"재개" 버튼**
2. Management → Jetson `ResumeConveyor` RPC 전송
3. 대기 중 태스크 순차 재시작

### 4.7 교대 인수인계 (Shift Handover)
- 이전 교대의 알람 해결 여부 확인
- 진행 중 주문 목록 인계
- 장비별 이상 여부 브리핑
- 인수 시각 로그 기록 (수기 또는 UI)

---

## 5. 일상 운영 플로우 (하루 예시)

### 5.1 오전 시작
1. Factory Operator: PyQt 기동, 시스템 상태 점검
2. Admin: 야간 접수된 주문 검토, 승인
3. Factory Operator: 승인된 주문 확인 후 우선순위 정리
4. **생산 시작 버튼** 클릭 → 첫 주문 착수

### 5.2 주간 운영
- 30분마다 대시보드 확인
- AMR 배터리 모니터링
- 불량품 발생 시 원인 기록 (재료? 온도? 장비?)
- 중간 교대 시 간략 인계

### 5.3 오후 마감
- 당일 생산 실적 집계
- Admin 이 리포트 확인
- 내일 생산 계획 사전 점검
- 긴급 유지보수 스케줄

---

## 6. 문제 대응 (Troubleshooting)

### 6.1 "생산 시작 버튼을 눌렀는데 반응이 없어요"
- Management Service 연결 확인 (PyQt 상태 표시줄)
- 네트워크 (Tailscale) 확인
- Management 로그 확인: `tail -f backend/management/logs/server.log`

### 6.2 "AMR이 계속 FAILED 상태예요"
- 물리적 장애물 확인
- 배터리 확인 (충전 필요 여부)
- `trans_err_log` 마지막 행 err_msg 확인
- 복구 후 "수리 완료" 버튼

### 6.3 "컨베이어가 안 움직여요"
- ESP32 전원 / 케이블 확인
- Jetson Serial 연결 (`/dev/ttyUSB0`)
- Management `WatchConveyorCommands` stream 활성 여부
- Jetson 로그: `journalctl -u esp_bridge.service`

### 6.4 "검사 결과가 계속 FAIL이에요"
- 카메라 렌즈 청결 확인
- 조명 상태 확인
- 제품 표면 이상 여부 (작업자 육안 확인)
- AI 모델 임계값 확인 (개발팀 문의)

### 6.5 "주문을 제출했는데 상태가 안 변해요"
- Interface Service 상태 확인 (`/api/management/health` 확인)
- 관리자에게 수동 검토 요청
- DB `ord_stat` 직접 조회 (Admin)

### 6.6 "PyQt 창이 종료될 때 크래시가 납니다"
- 2026-04 경험: QThread 정리 누락
- 정상 종료: 창의 X 버튼이 아닌 메뉴 `파일 > 종료` 사용
- 기술팀에 로그 공유 (exit 134 SIGABRT)

---

## 7. 지원 채널

### 7.1 기술 지원
- **개발팀 리드**: ibkim (kiminbean@gmail.com)
- **Jetson/펌웨어**: 공장 운영팀
- **DB 서버**: yejin-laptop 소유자

### 7.2 응급 복구
| 상황 | 즉시 조치 |
|---|---|
| AWS RDS 접속 안됨 | Tailscale 재연결, DB Beaver 로 수동 확인 |
| 로컬 PG 다운 | yejin-laptop 점검 요청 |
| Factory Operator PC 부팅 실패 | 교대 PC 로 대체 |
| 공장 전력 차단 | 수동 프로토콜 (물리 안전 우선) |

### 7.3 버그 리포트
GitHub Issues (내부 저장소) 에 다음 정보 포함:
- 발생 시각
- 사용자 (Customer/Admin/Operator)
- 재현 단계
- 스크린샷 / 로그
- 기대 동작 vs 실제 동작

---

## 8. 보안 / 데이터 보호 (사용자 가이드)

### 8.1 비밀번호
- 최소 12자, 대소문자·숫자·특수문자 조합
- 정기 변경 (분기별)
- 공유 금지

### 8.2 접근 권한
- 고객: 자신의 주문만 조회 가능
- 관리자: 전체 주문 + 제품·장비 관리
- 공장 운영자: 공정 관리 + 로컬 DB 읽기/쓰기

### 8.3 외부 공유 금지
- 고객 정보, 주문 상세
- Confluence 내부 페이지 (READ-ONLY)
- DB 자격증명 (평문)

### 8.4 정기 백업
- DB 스냅샷: 일일 (운영팀 자동화 예정)
- 주요 문서: Git 저장소
- Confluence: launchd 매일 09:07 동기화

---

## 9. 용어 빠른 참조 (사용자 관점)

| 용어 | 의미 |
|---|---|
| 접수 / RCVD | 고객이 제출한 상태 |
| 승인 / APPR | 관리자가 승인, 생산 대기 |
| 생산 중 / MFG | 공장에서 제작 중 |
| 출하 준비 / DONE | 검사 통과, 출고 준비 |
| 출하 중 / SHIP | 배송 진행 |
| 완료 / COMP | 고객 인수 완료 |
| AMR | 자율주행 로봇 (이송) |
| RA | 로봇팔 |
| INSP | 검사 |
| 패턴 | 주형용 원형 모델 |
| 탈형 | 냉각 후 주형 제거 |

---

## 10. 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | V6 | 초기 작성. 고객 / 관리자 / 공장 운영자 매뉴얼 통합 |
