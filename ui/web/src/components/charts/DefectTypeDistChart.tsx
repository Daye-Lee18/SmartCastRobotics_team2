"use client";

import { useRef, useState, useEffect } from "react";
import { PieChart, Pie, Cell, Tooltip } from "recharts";
import { mockDefectTypeStats } from "@/lib/mock-data";

export default function DefectTypeDistChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(300);

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

  const data = mockDefectTypeStats.map((d) => ({ name: d.type, value: d.count }));

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <PieChart width={width} height={200}>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {mockDefectTypeStats.map((item, index) => (
            <Cell key={`cell-${index}`} fill={item.color} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, name) => [`${value}건`, name]}
          contentStyle={{ fontSize: 13, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
      </PieChart>
      <ul className="mt-3 space-y-1">
        {mockDefectTypeStats.map((item) => (
          <li key={item.type} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-gray-700">{item.type}</span>
            </span>
            <span className="font-medium text-gray-800">{item.count}건 ({item.percentage}%)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
