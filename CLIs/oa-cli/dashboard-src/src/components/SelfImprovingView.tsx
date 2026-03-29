import { motion } from "framer-motion";
import { SelfImprovingCard } from "./SelfImprovingCard";
import { SelfImprovingDetailSection } from "./SelfImprovingDetailSection";
import type { GoalSummary, CronRun, AgentActivity } from "../types";

interface Props {
  goals: GoalSummary[];
  goalMetrics: Record<string, unknown[]>;
  cronRuns?: CronRun[];
  teamHealth?: AgentActivity[];
}

export function SelfImprovingView({ goals, goalMetrics, cronRuns = [], teamHealth = [] }: Props) {
  // Filter to only self-improvement goal
  const selfImprovingGoal = goals.find((g) => g.id === "self_improvement");

  // Get all goals for display (we'll show the self-improving one prominently)
  const otherGoals = goals.filter((g) => g.id !== "self_improvement");

  if (!selfImprovingGoal) {
    return (
      <div className="space-y-5">
        {/* Welcome/Intro */}
        <motion.div
          className="glass-card p-8 text-center"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="text-4xl mb-4">🚀</div>
          <h2 className="text-lg font-bold text-gray-800 mb-2">
            System Self-Improving
          </h2>
          <p className="text-sm text-gray-500 max-w-md mx-auto">
            Tracks whether your agent team is continuously improving by measuring
            issues resolved, new skills added, and knowledge captured.
          </p>
        </motion.div>

        {/* Empty state */}
        {goals.length === 0 && (
          <div className="glass-card p-12 text-center">
            <p className="text-lg font-semibold text-gray-400">No data yet</p>
            <p className="text-sm text-gray-300 mt-2">
              Run <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">oa collect</code> to gather metrics
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Welcome/Intro */}
      <motion.div
        className="glass-card p-6"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-start gap-4">
          <div className="text-3xl">🚀</div>
          <div className="flex-1">
            <h2 className="text-base font-bold text-gray-800">
              System Self-Improving
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              Tracks whether your agent team is continuously improving. Higher scores indicate
              the team is actively resolving issues, adding new capabilities, and capturing knowledge.
            </p>
          </div>
          <ScoreCircle score={selfImprovingGoal.metrics.self_improvement_score?.value ?? null} />
        </div>
      </motion.div>

      {/* Self-Improving Goal Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 items-stretch">
        <div>
          <SelfImprovingCard goal={selfImprovingGoal} index={0} />
        </div>
        <SelfImprovingDetailSection
          goal={selfImprovingGoal}
          index={0}
          metrics={goalMetrics[selfImprovingGoal.id] || []}
          cronRuns={cronRuns}
          teamHealth={teamHealth}
        />
      </div>

      {/* Other goals as smaller cards */}
      {otherGoals.length > 0 && (
        <motion.div
          className="pt-4 border-t border-gray-100"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-[0.15em] mb-3">
            Other Goals
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {otherGoals.map((goal, i) => (
              <MiniGoalCard key={goal.id} goal={goal} index={i} />
            ))}
          </div>
        </motion.div>
      )}

      {/* Footer */}
      <motion.div
        className="text-center py-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <span className="text-[10px] text-gray-300 font-mono tracking-wider uppercase">
          Self-Improving View — tracking agent team growth
        </span>
      </motion.div>
    </div>
  );
}

function ScoreCircle({ score }: { score: number | null }) {
  const color =
    score === null
      ? "#94A3B8"
      : score >= 70
      ? "#34D399"
      : score >= 40
      ? "#FBBF24"
      : "#F87171";

  const percentage = score !== null ? Math.round(score) : 0;

  // SVG circle parameters
  const size = 64;
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          style={{
            filter: `drop-shadow(0 0 4px ${color}40)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold" style={{ color }}>
          {score !== null ? `${percentage}%` : "—"}
        </span>
      </div>
    </div>
  );
}

function MiniGoalCard({ goal, index }: { goal: GoalSummary; index: number }) {
  const color =
    goal.healthStatus === "healthy"
      ? "#34D399"
      : goal.healthStatus === "warning"
      ? "#FBBF24"
      : goal.healthStatus === "critical"
      ? "#F87171"
      : "#94A3B8";

  const primary = Object.values(goal.metrics)[0];

  return (
    <motion.div
      className="glass-card p-4 cursor-pointer"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.05 }}
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">{goal.name}</h4>
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
      {primary && (
        <div className="text-lg font-bold" style={{ color }}>
          {primary.value !== null ? `${Math.round(primary.value * 10) / 10}` : "—"}
          {primary.unit === "%" && "%"}
        </div>
      )}
    </motion.div>
  );
}
