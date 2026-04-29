<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-27 -->

# src/components

재사용 React 컴포넌트 — 레이아웃, 팩토리 맵, 차트, 위젯.

## Key Files

| File | Description |
|------|-------------|
| `Header.tsx` | 메인 헤더 컴포넌트 |
| `Sidebar.tsx` | 내비게이션 사이드바 |
| `SmartCastHeader.tsx` | SmartCast 브랜드 헤더 |
| `SmartCastLogo.tsx` | 로고 컴포넌트 |
| `AdminShell.tsx` | 관리자 레이아웃 래퍼 |
| `FactoryMap.tsx` | thin re-export → `factory-map/index` |
| `FactoryMap3D.tsx` | 3D 팩토리 맵 (Three.js) |
| `FactoryMap3DCanvas.tsx` | 3D 캔버스 렌더러 |
| `FactoryMapEditor.tsx` | 팩토리 맵 편집기 |
| `DevHandoffAckButton.tsx` | 개발용 핸드오프 ACK 버튼 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `charts/` | 데이터 시각화 차트 (defect rate, weekly production) |
| `factory-map/` | 4뷰 통합 컨트롤룸 (3D 렌더 / 인터랙티브 / 공정 레이아웃 / 실시간 3D) — 13 파일 분할 |

## For AI Agents

### Common Patterns
- 함수형 컴포넌트 + TypeScript props 인터페이스
- 3D 맵: Three.js (FactoryMap3D → FactoryMap3DCanvas)
- 차트: recharts 라이브러리
- `AdminShell`로 admin 페이지 레이아웃 일관성 유지

## Dependencies

### Internal
- `src/lib/api.ts` — 데이터 fetch
- `src/lib/types.ts` — 타입 정의

### External
- React, recharts, three.js, lucide-react
