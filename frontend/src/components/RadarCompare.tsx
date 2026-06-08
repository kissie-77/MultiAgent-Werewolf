import React, { useEffect, useState } from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { ApiClient } from "../api/client";
import { ModelDetail } from "../api/types";

interface RadarCompareProps {
  selectedIds: string[];
}

const DIMENSION_KEYS = [
  { key: "logic", label: "逻辑说服" },
  { key: "deception", label: "狼夜诡策" },
  { key: "cooperation", label: "大局策略" },
  { key: "persuasion", label: "结果预判" },
  { key: "survivability", label: "绝境生存" },
] as const;

const colors = ["#eab308", "#3b82f6", "#ef4444", "#10b981", "#a855f7"];

export default function RadarCompare({ selectedIds }: RadarCompareProps) {
  const [models, setModels] = useState<ModelDetail[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedIds.length === 0) {
      setModels([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all(selectedIds.map((id) => ApiClient.getModelDetail(id).catch(() => null)))
      .then((results) => {
        if (cancelled) return;
        setModels(results.filter((r): r is ModelDetail => r !== null));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedIds]);

  if (selectedIds.length === 0) return null;

  // Build radar data from real model radarStats
  const data = DIMENSION_KEYS.map(({ key, label }) => {
    const row: Record<string, string | number> = { subject: label, fullMark: 100 };
    models.forEach((m, i) => {
      row[m.name] = m.radarStats?.[key] ?? 0;
    });
    return row;
  });

  return (
    <div className="w-full h-[400px]">
      {loading ? (
        <div className="flex items-center justify-center h-full text-zinc-500 font-mono text-xs tracking-widest">
          <div className="w-5 h-5 border-2 border-t-amber-500 border-zinc-800 rounded-full animate-spin mr-3" />
          同步模型灵能数据...
        </div>
      ) : models.length === 0 ? (
        <div className="flex items-center justify-center h-full text-zinc-600 font-mono text-xs tracking-widest">
          无法获取模型雷达数据
        </div>
      ) : (
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

            {models.map((m, index) => (
              <Radar
                key={m.id}
                name={m.name}
                dataKey={m.name}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
