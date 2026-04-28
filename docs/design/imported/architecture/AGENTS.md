<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# docs/architecture

12개 컴포넌트 아키텍처 설계 문서 (HTML + Mermaid 다이어그램).

## Key Files

| File | Description |
|------|-------------|
| `index.html` | 아키텍처 문서 인덱스 |
| `_shared.css` | 공용 스타일시트 |
| `01_office_ui.html` | Office UI 아키텍처 |
| `02_order_api_db.html` | 주문 API/DB 아키텍처 |
| `03_factory_manager_ui.html` | Factory Manager UI |
| `04_work_order_scheduler.html` | 작업 지시 스케줄러 |
| `05_production_lane_queue.html` | 생산 레인 큐 |
| `06_shipment_lane_queue.html` | 출고 레인 큐 |
| `07_workflow_task_manager.html` | 워크플로우 태스크 매니저 |
| `08_ready_task_pool.html` | 준비 태스크 풀 |
| `09_global_task_allocator.html` | 글로벌 태스크 할당자 |
| `10_resource_reservation_manager.html` | 리소스 예약 관리자 |
| `11_robot_cell_executors.html` | 로봇 셀 실행기 |
| `12_execution_monitor.html` | 실행 모니터 |

## For AI Agents

### Working In This Directory
- HTML 파일은 브라우저로 열어야 다이어그램 렌더링
- Mermaid.js 기반 다이어그램 포함
- `_shared.css` 로 일관된 스타일링
- 문서 내용은 Confluence 기반 — 수정 시 Confluence도 업데이트 필요
