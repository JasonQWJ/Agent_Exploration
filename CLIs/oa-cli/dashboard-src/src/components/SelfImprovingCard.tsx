import { motion } from "framer-motion";
import type { GoalSummary } from "../types";

function healthColor(status: string): string {
  switch (status) {
    case "healthy": return "#34D399";
    case "warning": return "#FBBF24";
    case "critical": return "#F87171";
    default: return "#94A3B8";
  }
}

function formatValue(value: number | null, unit: string): string {
  if (value === null) return "—";
  if (unit === "%" || unit === "percent") return `${Math.round(value * 10) / 10}%`;
  if (unit === "count") return `${Math.round(value)}`;
  return `${Math.round(value * 10) / 10}${unit ? ` ${unit}` : ""}`;
}

function formatMetricName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface Props {
  goal: GoalSummary;
  index: number;
}

export function SelfImprovingCard({ goal, index }: Props) {
  const color = healthColor(goal.healthStatus);
  const metrics = Object.entries(goal.metrics);
  const primary = metrics.find(([k]) => k === "self_improvement_score");
  const subMetrics = metrics.filter(([k]) => k !== "self_improvement_score");

  // Get breakdown from primary metric if available
  const breakdown = primary?.[1]?.breakdown as Record<string, number> | undefined;

  return (
    <motion.div
      className="goal-card p-5 h-full"
      style={{ "--goal-health-color": color } as React.CSSProperties}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">{goal.name}</h3>
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}40` }}
        />
      </div>

      {/* Primary Metric */}
      {primary && (
        <div className="mb-3">
          <div className="text-3xl font-bold" style={{ color }}>
            {formatValue(primary[1].value, primary[1].unit)}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">
              {formatMetricName(primary[0])}
            </span>
            <TrendBadge trend={primary[1].trend} />
          </div>
        </div>
      )}

      {/* Sub-metrics */}
      {subMetrics.length > 0 && (
        <div className="border-t border-gray-100 pt-2 mt-2 space-y-1.5">
          {subMetrics.map(([name, m]) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-[11px] text-gray-400">{formatMetricName(name)}</span>
              <span
                className="text-[11px] font-semibold"
                style={{ color: healthColor(m.status) }}
              >
                {formatValue(m.value, m.unit)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Breakdown visualization */}
      {breakdown && (
        <div className="mt-3 pt-2 border-t border-gray-100">
          <div className="text-[9px] text-gray-400 uppercase tracking-wider mb-2">
            Component Scores
          </div>
          <div className="space-y-1.5">
            <ScoreBar
              label="Issues"
              score={breakdown.issue_score ?? 0}
              value={breakdown.issues_resolved ?? 0}
              color="#34D399"
            />
            <ScoreBar
              label="Skills"
              score={breakdown.skill_score ?? 0}
              value={breakdown.skills_added ?? 0}
              color="#60A5FA"
            />
            <ScoreBar
              label="Memory"
              score={breakdown.memory_score ?? 0}
              value={breakdown.memory_entries ?? 0}
              color="#A78BFA"
            />
          </div>
        </div>
      )}
    </motion.div>
  );
}

function ScoreBar({
  label,
  score,
  value,
  color,
}: {
  label: string;
  score: number;
  value: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-10">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, score)}%` }}
          transition={{ duration: 0.8, delay: 0.3 }}
        />
      </div>
      <span className="text-[10px] text-gray-400 w-6 text-right">{value}</span>
    </div>
  );
}

function TrendBadge({ trend }: { trend: number | null }) {
  if (trend === null || trend === undefined) return null;
  if (trend > 0) {
    return <span className="text-[11px] font-medium text-emerald-600">▲ +{trend}</span>;
  }
  if (trend < 0) {
    return <span className="text-[11px] font-medium text-red-500">▼ {trend}</span>;
  }
  return <span className="text-[11px] font-medium text-gray-400">─</span>;
}
