"use client";

import { useRef, useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { mockProductionMetrics } from "@/lib/mock-data";

export default function ProductionVsDefectsChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(500);

  useEffect(() => {
    function updateSize() {
      if (containerRef.current) {
        setWidth(containerRef.current.clientWidth);
      }
    }
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  return (
    <div ref={containerRef} style={{ width: "100%", height: 260 }}>
      <BarChart
        width={width}
        height={260}
        data={mockProductionMetrics}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6b7280" }} />
        <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} />
        <Tooltip contentStyle={{ fontSize: 13, borderRadius: 8, border: "1px solid #e5e7eb" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="production" name="생산량" fill="#3b82f6" radius={[3, 3, 0, 0]} />
        <Bar dataKey="defects" name="불량" fill="#ef4444" radius={[3, 3, 0, 0]} />
      </BarChart>
    </div>
  );
}
