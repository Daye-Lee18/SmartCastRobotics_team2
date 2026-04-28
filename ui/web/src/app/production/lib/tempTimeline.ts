// 용해로 온도 시뮬레이션 데이터 생성 (30분, 1차 지연 곡선 + 노이즈).

import type { ProcessStageData } from "@/lib/types";

export function buildTempTimeline(stages: ProcessStageData[]) {
  const meltingStage = stages.find((s) => s.stage === "melting");
  return Array.from({ length: 30 }, (_, i) => {
    const minute = i + 1;
    const target = meltingStage?.targetTemperature ?? 1450;
    const current = Math.round(
      target - (target - 1200) * Math.exp(-0.12 * minute) + (Math.random() - 0.5) * 8
    );
    return {
      time: `${minute}분`,
      현재온도: current,
      목표온도: target,
    };
  });
}
