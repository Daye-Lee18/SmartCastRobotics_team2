<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# monitoring/app/widgets

재사용 PyQt5 UI 위젯 — AMR, 컨베이어, 카메라, 차트, 게이지.

## Key Files

| File | Description |
|------|-------------|
| `amr_card.py` | AMR 상태 카드 위젯 |
| `conveyor_card.py` | 컨베이어 상태 카드 위젯 |
| `camera_view.py` | 카메라 피드 뷰어 |
| `charts.py` | 차트/그래프 위젯 |
| `gauges.py` | 게이지/미터 위젯 |
| `sorter_dial.py` | 소터 다이얼 위젯 |
| `factory_map.py` | 팩토리 맵 위젯 |
| `warehouse_rack.py` | 창고 랙 시각화 |
| `defect_panels.py` | 결함 디스플레이 패널 |
| `alert_widgets.py` | 알림/토스트 위젯 |

## For AI Agents

### Common Patterns
- QWidget 또는 QFrame 서브클래싱
- 시그널/슬롯으로 workers/와 연결
- `styles.qss` 로 테마 일관성 유지
