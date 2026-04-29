"use client";

import dynamic from "next/dynamic";
import { BarChart3 } from "lucide-react";
import type { ProductionMetric } from "@/lib/types";

// Recharts: SSR 비활성화 동적 임포트.
const BarChartComponent = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });
const Legend = dynamic(() => import("recharts").then((m) => m.Legend), { ssr: false });

interface HourlyProductionChartProps {
  hourlyProduction: ProductionMetric[];
}

// 금일 24시간 시간별 생산량 / 불량 막대 차트 + 합계 footer.
export function HourlyProductionChart({ hourlyProduction }: HourlyProductionChartProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-emerald-500" />
        시간별 생산량
      </h3>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChartComponent data={hourlyProduction}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} iconSize={10} />
            <Bar dataKey="production" name="생산량" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="defects" name="불량" fill="#f43f5e" radius={[4, 4, 0, 0]} />
          </BarChartComponent>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
        <span>
          금일 총 생산:{" "}
          <strong className="text-gray-800">
            {hourlyProduction.reduce((sum, h) => sum + h.production, 0)}
            개
          </strong>
        </span>
        <span>
          금일 불량:{" "}
          <strong className="text-red-600">
            {hourlyProduction.reduce((sum, h) => sum + h.defects, 0)}
            개
          </strong>
        </span>
      </div>
    </div>
  );
}
