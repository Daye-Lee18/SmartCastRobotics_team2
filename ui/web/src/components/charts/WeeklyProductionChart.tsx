"use client";

import { useRef, useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { ProductionMetric } from "@/lib/types";

interface WeeklyProductionChartProps {
  data: ProductionMetric[];
}

export default function WeeklyProductionChart({ data }: WeeklyProductionChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 500, height: 220 });

  useEffect(() => {
    function updateSize() {
      if (containerRef.current) {
        setSize({ width: containerRef.current.clientWidth, height: 220 });
      }
    }
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  return (
    <div ref={containerRef} style={{ width: "100%", height: 220 }}>
      <AreaChart
        width={size.width}
        height={size.height}
        data={data}
        margin={{ top: 4, right: 8, left: -20, bottom: 0 }}
      >
        <defs>
          <linearGradient id="colorProduction" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorDefects" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: "8px", fontSize: "12px" }}
          labelStyle={{ color: "#374151", fontWeight: 600 }}
        />
        <Area type="monotone" dataKey="production" name="생산량" stroke="#3b82f6" strokeWidth={2} fill="url(#colorProduction)" />
        <Area type="monotone" dataKey="defects" name="불량" stroke="#ef4444" strokeWidth={2} fill="url(#colorDefects)" />
      </AreaChart>
    </div>
  );
}
