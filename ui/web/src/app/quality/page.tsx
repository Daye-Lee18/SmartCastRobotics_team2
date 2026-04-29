"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Camera,
  Loader2,
  PieChart,
  ShieldCheck,
} from "lucide-react";
import {
  fetchInspectionStandards,
  fetchInspections,
  fetchQualityStats,
  fetchSorterLogs,
} from "@/lib/api";
import type { InspectionRecord, InspectionStandard, SorterLog } from "@/lib/types";
import { FailedInspectionsTable } from "./components/FailedInspectionsTable";
import { InspectionStandardsPanel } from "./components/InspectionStandardsPanel";
import { QualityStatsCards } from "./components/QualityStatsCards";
import { SorterStatus } from "./components/SorterStatus";
import { VisionCameraFeed } from "./components/VisionCameraFeed";

// Recharts 동적 임포트 (SSR 비활성화)
const DefectTypeDistChart = dynamic(
  () => import("@/components/charts/DefectTypeDistChart"),
  { ssr: false, loading: () => <div className="h-[260px] bg-gray-50 rounded-xl animate-pulse" /> }
);

const DefectRateChart = dynamic(
  () => import("@/components/charts/DefectRateChart"),
  { ssr: false, loading: () => <div className="h-[260px] bg-gray-50 rounded-xl animate-pulse" /> }
);

const ProductionVsDefectsChart = dynamic(
  () => import("@/components/charts/ProductionVsDefectsChart"),
  { ssr: false, loading: () => <div className="h-[260px] bg-gray-50 rounded-xl animate-pulse" /> }
);

export default function QualityPage(): React.JSX.Element {
  const [inspections, setInspections] = useState<InspectionRecord[]>([]);
  const [standards, setStandards] = useState<InspectionStandard[]>([]);
  const [sorterLogs, setSorterLogs] = useState<SorterLog[]>([]);
  const [qualityStats, setQualityStats] = useState<{
    total: number;
    passed: number;
    failed: number;
    defectRate: number;
    defectTypes: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [inspData, statsData, stdData, sorterData] = await Promise.all([
          fetchInspections(),
          fetchQualityStats(),
          fetchInspectionStandards(),
          fetchSorterLogs(),
        ]);
        setInspections(inspData);
        setQualityStats(statsData);
        setStandards(stdData);
        setSorterLogs(sorterData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "데이터를 불러오는 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // 검사 통계 계산
  const stats = useMemo(() => {
    if (qualityStats) {
      const passRate =
        qualityStats.total > 0 ? (qualityStats.passed / qualityStats.total) * 100 : 0;
      return {
        total: qualityStats.total,
        passCount: qualityStats.passed,
        failCount: qualityStats.failed,
        passRate,
      };
    }
    const total = inspections.length;
    const passCount = inspections.filter((i) => i.result === "pass").length;
    const failCount = total - passCount;
    const passRate = total > 0 ? (passCount / total) * 100 : 0;
    return { total, passCount, failCount, passRate };
  }, [qualityStats, inspections]);

  // 불량 유형 TOP 3
  const top3Defects = useMemo(() => {
    if (qualityStats?.defectTypes) {
      return Object.entries(qualityStats.defectTypes)
        .map(([type, count]) => ({
          type,
          count,
          percentage: stats.failCount > 0 ? (count / stats.failCount) * 100 : 0,
          color: "",
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 3);
    }
    return [];
  }, [qualityStats, stats.failCount]);

  // 불량 검사 로그만 추출
  const failedInspections = useMemo(
    () => inspections.filter((i) => i.result === "fail"),
    [inspections]
  );

  // 최신 sorter 로그
  const latestSorter = sorterLogs.length > 0 ? sorterLogs[0] : null;
  // 가장 최근 검사 결과
  const latestInspection = inspections.length > 0 ? inspections[0] : null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={36} className="animate-spin text-blue-500" />
          <p className="text-base text-gray-500">품질 데이터를 불러오는 중...</p>
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-[1600px] mx-auto space-y-6">
        {/* 페이지 헤더 */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">품질 검사 대시보드</h1>
            <p className="text-base text-gray-500 mt-0.5">
              AI 비전 기반 실시간 품질 검사 현황 및 분류 장치 모니터링
            </p>
          </div>
        </div>

        {/* TOP: 검사 통계 카드 */}
        <QualityStatsCards
          total={stats.total}
          passCount={stats.passCount}
          failCount={stats.failCount}
          passRate={stats.passRate}
          top3Defects={top3Defects}
        />

        {/* CENTER: 비전/센서 피드 + 불량 유형 차트 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          {/* 비전 카메라 피드 + 분류 장치 상태 */}
          <div className="lg:col-span-2 space-y-6 flex flex-col">
            {/* 비전 카메라 시뮬레이션 */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                  <Camera className="w-4 h-4 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">비전 검사 피드</h2>
                <span className="ml-auto flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-green-100 text-green-700">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  실시간
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <VisionCameraFeed latestInspection={latestInspection} />
                <SorterStatus latestSorter={latestSorter} />
              </div>
            </div>

            {/* 불량률 추이 + 생산량 vs 불량 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-full">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                    <Activity className="w-4 h-4 text-red-500" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">불량률 추이</h2>
                </div>
                <DefectRateChart />
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-full">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                    <BarChart3 className="w-4 h-4 text-blue-600" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">생산량 vs 불량</h2>
                </div>
                <ProductionVsDefectsChart />
              </div>
            </div>
          </div>

          {/* 우측: 불량 유형 분포 + 검사 기준 */}
          <div className="flex flex-col gap-6">
            {/* 불량 유형 분포 차트 */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
                  <PieChart className="w-4 h-4 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">불량 유형 분포</h2>
              </div>
              <DefectTypeDistChart />
            </div>

            {/* 검사 기준 참조 패널 */}
            <InspectionStandardsPanel standards={standards} />
          </div>
        </div>

        {/* BOTTOM: 불량 검사 로그 테이블 */}
        <FailedInspectionsTable failedInspections={failedInspections} />
      </div>
    </div>
  );
}
