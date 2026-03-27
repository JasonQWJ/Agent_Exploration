import { motion } from "framer-motion";
import type { GoalSummary, CronRun, AgentActivity } from "../types";

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
  metrics: unknown[];
  cronRuns: CronRun[];
  teamHealth: AgentActivity[];
}

export function SelfImprovingDetailSection({ goal, index, metrics, cronRuns, teamHealth }: Props) {
  const color = healthColor(goal.healthStatus);
  const metricsList = Object.entries(goal.metrics);
  const primaryMetric = metricsList.find(([k]) => k === "self_improvement_score");
  const breakdown = primaryMetric?.[1]?.breakdown as Record<string, number> | undefined;

  // Get trend data from metrics history
  const trendData = metrics.filter((m: any) => m.metric === "self_improvement_score").slice(-7);

  return (
    <motion.div
      className="detail-section h-full"
      style={{ "--goal-color": color } as React.CSSProperties}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 + 0.1 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{goal.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Tracks agent team growth and continuous improvement
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Status</span>
          <span
            className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider"
            style={{
              backgroundColor: `${color}20`,
              color,
            }}
          >
            {goal.healthStatus}
          </span>
        </div>
      </div>

      {/* Three-column metric cards */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {metricsList
          .filter(([k]) => k !== "self_improvement_score")
          .map(([name, m]) => (
            <MetricCard key={name} name={name} metric={m} />
          ))}
      </div>

      {/* Component breakdown */}
      {breakdown && (
        <div className="glass-card p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Improvement Components
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <ComponentCard
              icon="🐛"
              label="Issues Resolved"
              value={breakdown.issues_resolved ?? 0}
              score={breakdown.issue_score ?? 0}
              color="#34D399"
              description="Tasks closed today"
            />
            <ComponentCard
              icon="🧩"
              label="Skills Added"
              value={breakdown.skills_added ?? 0}
              score={breakdown.skill_score ?? 0}
              color="#60A5FA"
              description="New capabilities"
            />
            <ComponentCard
              icon="📝"
              label="Memory Entries"
              value={breakdown.memory_entries ?? 0}
              score={breakdown.memory_score ?? 0}
              color="#A78BFA"
              description="Knowledge captured"
            />
          </div>
        </div>
      )}

      {/* Trend mini-chart */}
      {trendData.length > 1 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            7-Day Trend
          </h4>
          <MiniSparkline data={trendData} color={color} />
        </div>
      )}
    </motion.div>
  );
}

function MetricCard({ name, metric }: { name: string; metric: any }) {
  return (
    <div className="glass-card p-3">
      <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">
        {formatMetricName(name)}
      </div>
      <div className="text-xl font-bold" style={{ color: healthColor(metric.status) }}>
        {formatValue(metric.value, metric.unit)}
      </div>
      {metric.trend !== null && metric.trend !== undefined && (
        <TrendBadge trend={metric.trend} />
      )}
    </div>
  );
}

function ComponentCard({
  icon,
  label,
  value,
  score,
  color,
  description,
}: {
  icon: string;
  label: string;
  value: number;
  score: number;
  color: string;
  description: string;
}) {
  return (
    <div className="text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-lg font-bold text-gray-800">{value}</div>
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className="text-[9px] text-gray-400">{description}</div>
      <div className="mt-2 h-1 bg-gray-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, score)}%` }}
          transition={{ duration: 0.8, delay: 0.3 }}
        />
      </div>
    </div>
  );
}

function TrendBadge({ trend }: { trend: number | null }) {
  if (trend === null || trend === undefined) return null;
  if (trend > 0) {
    return <span className="text-[10px] font-medium text-emerald-600">▲ +{trend}</span>;
  }
  if (trend < 0) {
    return <span className="text-[10px] font-medium text-red-500">▼ {trend}</span>;
  }
  return <span className="text-[10px] font-medium text-gray-400">─</span>;
}

function MiniSparkline({ data, color }: { data: any[]; color: string }) {
  const values = data.map((d) => d.value ?? 0);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const range = max - min || 1;

  const width = 200;
  const height = 40;
  const padding = 4;

  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - padding - ((v - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  });

  const pathD = points.length > 1 ? `M ${points.join(" L ")}` : "";

  return (
    <div className="w-full h-12 relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full"
        preserveAspectRatio="none"
      >
        {/* Area under the line */}
        {pathD && (
          <>
            <defs>
              <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                <stop offset="100%" stopColor={color} stopOpacity="0" />
              </linearGradient>
            </defs>
            <motion.path
              d={`${pathD} L ${width},${height} L 0,${height} Z`}
              fill="url(#sparklineGradient)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            />
            <motion.path
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1, ease: "easeOut" }}
            />
          </>
        )}
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[8px] text-gray-300 px-1">
        {data.map((d: any, i: number) => (
          <span key={i}>{d.date?.slice(5) ?? ""}</span>
        ))}
      </div>
    </div>
  );
}
