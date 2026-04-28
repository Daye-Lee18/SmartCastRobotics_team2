"use client";

import { Activity, AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchEquipment,
  fetchProcessStages,
  fetchProductionMetrics,
} from "@/lib/api";
import type {
  Equipment,
  EquipmentStatus,
  ProcessStageData,
  ProductionMetric,
} from "@/lib/types";
import { CoolingProgressCard } from "./components/CoolingProgressCard";
import { EmergencyStopButton } from "./components/EmergencyStopButton";
import { EquipmentControlPanel } from "./components/EquipmentControlPanel";
import { HourlyProductionChart } from "./components/HourlyProductionChart";
import { MeltingTempChart } from "./components/MeltingTempChart";
import { MoldingPouringStats } from "./components/MoldingPouringStats";
import { ProcessFlow } from "./components/ProcessFlow";
import { ProcessParametersTable } from "./components/ProcessParametersTable";
import { buildTempTimeline } from "./lib/tempTimeline";

export default function ProductionPage() {
  const [processStages, setProcessStages] = useState<ProcessStageData[]>([]);
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([]);
  const [hourlyProduction, setHourlyProduction] = useState<ProductionMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [stagesData, eqData, metricsData] = await Promise.all([
          fetchProcessStages(),
          fetchEquipment(),
          fetchProductionMetrics(),
        ]);
        setProcessStages(stagesData);
        setEquipmentList(eqData);
        setHourlyProduction(metricsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "데이터를 불러오는 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // 설비별 자동/수동 모드 토글 상태
  const [autoModes, setAutoModes] = useState<Record<string, boolean>>({});
  // 설비별 현재 상태
  const [equipmentStatuses, setEquipmentStatuses] = useState<Record<string, EquipmentStatus>>({});
  // 상태 변경 시 시각 피드백용 (최근 변경된 설비 ID)
  const [recentlyChanged, setRecentlyChanged] = useState<string | null>(null);

  // 설비 데이터 로드 후 초기화
  useEffect(() => {
    if (equipmentList.length > 0) {
      const modes: Record<string, boolean> = {};
      const statuses: Record<string, EquipmentStatus> = {};
      equipmentList.forEach((eq) => {
        modes[eq.id] = true;
        statuses[eq.id] = eq.status;
      });
      setAutoModes(modes);
      setEquipmentStatuses(statuses);
    }
  }, [equipmentList]);

  const toggleMode = (equipmentId: string) => {
    setAutoModes((prev) => ({
      ...prev,
      [equipmentId]: !prev[equipmentId],
    }));
  };

  const changeEquipmentStatus = (equipmentId: string, newStatus: EquipmentStatus) => {
    setEquipmentStatuses((prev) => ({
      ...prev,
      [equipmentId]: newStatus,
    }));
    setRecentlyChanged(equipmentId);
    setTimeout(() => setRecentlyChanged(null), 800);
  };

  // 온도 타임라인 데이터
  const tempTimelineData = useMemo(() => buildTempTimeline(processStages), [processStages]);

  // 공정 단계별 데이터 매핑
  const stageDataMap = useMemo(() => {
    const map: Record<string, ProcessStageData> = {};
    processStages.forEach((s) => {
      map[s.stage] = s;
    });
    return map;
  }, [processStages]);

  const meltingStage = stageDataMap["melting"];
  const moldingStage = stageDataMap["molding"];
  const pouringStage = stageDataMap["pouring"];
  const coolingStage = stageDataMap["cooling"];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={36} className="animate-spin text-blue-500" />
          <p className="text-base text-gray-500">생산 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle size={36} className="text-red-400" />
          <p className="text-base text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 space-y-6">
      {/* ====== 페이지 헤더 ====== */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Activity className="w-7 h-7 text-blue-600" />
          생산 모니터링
        </h1>
        <span className="text-base text-gray-500">
          최종 갱신: {new Date().toLocaleTimeString("ko-KR")}
        </span>
      </div>

      {/* ====== 1. 공정 흐름 ====== */}
      <ProcessFlow stageDataMap={stageDataMap} />

      {/* ====== 2. 메인 3-컬럼 레이아웃 ====== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        {/* ── 중앙: 라이브 데이터 차트 ── */}
        <div className="lg:col-span-8 space-y-5">
          {/* 용해로 실시간 온도 그래프 */}
          <MeltingTempChart
            meltingStage={meltingStage}
            tempTimelineData={tempTimelineData}
          />

          {/* 조형/주탕 실시간 수치 + 시간별 생산량 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <MoldingPouringStats moldingStage={moldingStage} pouringStage={pouringStage} />
            <HourlyProductionChart hourlyProduction={hourlyProduction} />
          </div>
        </div>

        {/* ── 우측: 설비 제어 패널 ── */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          <EmergencyStopButton />
          <CoolingProgressCard coolingStage={coolingStage} />
          <EquipmentControlPanel
            equipmentList={equipmentList}
            equipmentStatuses={equipmentStatuses}
            autoModes={autoModes}
            recentlyChanged={recentlyChanged}
            onToggleMode={toggleMode}
            onChangeStatus={changeEquipmentStatus}
          />
        </div>
      </div>

      {/* ====== 3. 하단: 공정 파라미터 이력 테이블 ====== */}
      <ProcessParametersTable processStages={processStages} />
    </div>
  );
}
