"use client";

import { useRef, useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import { mockProductionMetrics } from "@/lib/mock-data";

export default function DefectRateChart() {
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
      <LineChart
        width={width}
        height={260}
        data={mockProductionMetrics}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6b7280" }} />
        <YAxis unit="%" tick={{ fontSize: 12, fill: "#6b7280" }} domain={[0, 12]} />
        <Tooltip
          formatter={(value) => [`${value}%`, "불량률"]}
          contentStyle={{ fontSize: 13, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <ReferenceLine
          y={5}
          stroke="#ef4444"
          strokeDasharray="4 4"
          label={{ value: "목표 5%", fill: "#ef4444", fontSize: 11, position: "insideTopRight" }}
        />
        <Line type="monotone" dataKey="defectRate" name="불량률" stroke="#f97316" strokeWidth={2} dot={{ r: 3, fill: "#f97316" }} activeDot={{ r: 5 }} />
      </LineChart>
    </div>
  );
}
