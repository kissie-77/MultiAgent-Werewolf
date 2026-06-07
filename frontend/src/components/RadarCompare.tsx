import React from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from "recharts";

interface RadarCompareProps {
  selectedIds: string[];
}

export default function RadarCompare({ selectedIds }: RadarCompareProps) {
  // Dummy data for radar
  const data = [
    { subject: '逻辑说服', A: 90, B: 85, C: 70, fullMark: 100 },
    { subject: '狼夜诡策', A: 95, B: 75, C: 60, fullMark: 100 },
    { subject: '大局策略', A: 85, B: 90, C: 80, fullMark: 100 },
    { subject: '结果预判', A: 80, B: 85, C: 75, fullMark: 100 },
    { subject: '绝境生存', A: 70, B: 65, C: 85, fullMark: 100 },
  ];

  const colors = ["#eab308", "#3b82f6", "#ef4444", "#10b981", "#a855f7"];

  if (selectedIds.length === 0) return null;

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#3f3f46" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#a1a1aa", fontSize: 12, fontFamily: "monospace" }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#71717a" }} axisLine={false} tickLine={false} />
          
          <Tooltip 
            contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", color: "#e4e4e7" }} 
            itemStyle={{ fontFamily: "monospace", fontSize: "12px" }} 
          />
          <Legend wrapperStyle={{ fontFamily: "monospace", fontSize: "12px", color: "#a1a1aa" }} />
          
          {selectedIds.map((id, index) => (
            <Radar
              key={id}
              name={id}
              dataKey={index === 0 ? "A" : index === 1 ? "B" : "C"}
              stroke={colors[index % colors.length]}
              fill={colors[index % colors.length]}
              fillOpacity={0.3}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
