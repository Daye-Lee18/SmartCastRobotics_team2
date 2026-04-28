"use client";

import dynamic from "next/dynamic";
import { Gauge, Thermometer } from "lucide-react";
import type { ProcessStageData } from "@/lib/types";

// Recharts: SSR 비활성화 동적 임포트.
const AreaChart = dynamic(() => import("recharts").then((m) => m.AreaChart), { ssr: false });
const Area = dynamic(() => import("recharts").then((m) => m.Area), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });
const ReferenceLine = dynamic(() => import("recharts").then((m) => m.ReferenceLine), { ssr: false });

interface MeltingTempChartProps {
  meltingStage?: ProcessStageData;
  tempTimelineData: Array<{ time: string; 현재온도: number; 목표온도: number }>;
}

// 용해로 30분 온도 곡선 (현재 vs 목표) + 가열 출력 헤더.
export function MeltingTempChart({ meltingStage, tempTimelineData }: MeltingTempChartProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Thermometer className="w-5 h-5 text-red-500" />
          용해로 실시간 온도
        </h3>
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            현재: <strong className="text-red-600">{meltingStage?.temperature ?? "-"}°C</strong>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            목표: <strong className="text-blue-600">{meltingStage?.targetTemperature ?? "-"}°C</strong>
          </span>
          <span className="flex items-center gap-1">
            <Gauge className="w-3.5 h-3.5 text-amber-500" />
            가열 출력: <strong className="text-amber-600">{meltingStage?.heatingPower ?? "-"}%</strong>
          </span>
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={tempTimelineData}>
            <defs>
              <linearGradient id="gradTemp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} interval={4} />
            <YAxis domain={[1100, 1500]} tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              formatter={(value) => [`${value}°C`]}
            />
            <ReferenceLine
              y={meltingStage?.targetTemperature ?? 1450}
              stroke="#3b82f6"
              strokeDasharray="6 3"
              label={{
                value: "목표",
                position: "right",
                fill: "#3b82f6",
                fontSize: 10,
              }}
            />
            <Area
              type="monotone"
              dataKey="현재온도"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#gradTemp)"
            />
            <Area
              type="monotone"
              dataKey="목표온도"
              stroke="#3b82f6"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              fill="none"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
