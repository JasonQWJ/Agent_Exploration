"""G2: Team Health Pipeline — tracks daily agent activity and memory discipline."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .base import Metric, Pipeline

if TYPE_CHECKING:
    from oa.core.config import ProjectConfig


class TeamHealthPipeline(Pipeline):
    """Built-in pipeline: scans OpenClaw sessions and memory files for agent activity."""

    goal_id = "team_health"

    def collect(self, date: str, config: "ProjectConfig") -> list[Metric]:
        from oa.core.tracing import Tracer

        tracer = Tracer(service="g2_team_health", db_path=config.db_path)

        with tracer.span("G2: Team Health", {"goal": "G2", "date": date}) as root:

            active_agents = 0
            memory_logged = 0

            # Pre-scan ClawTeam task activity so worker agents can be counted even
            # when ~/.clawteam/sessions is organized by team instead of by worker name.
            with tracer.span("Scan ClawTeam Tasks") as ct_span:
                ct_agent_ids = self._scan_clawteam_active_agents(
                    config.clawteam_home, date
                )
                ct_active_set = set(ct_agent_ids)
                ct_span.set_attribute("clawteam_active_agents", len(ct_active_set))

            # Step 1: Check each agent from config list (OpenClaw agents)
            with tracer.span("Scan Agent Activity") as scan:
                for agent in config.agents:
                    sessions = self._count_agent_sessions(
                        config.openclaw_home, agent.id, date,
                        clawteam_home=config.clawteam_home,
                    )
                    if sessions == 0 and agent.id in ct_active_set:
                        sessions = 1

                    has_memory = self._check_memory_logged(
                        config.openclaw_home, agent.id, date,
                        clawteam_home=config.clawteam_home,
                    )

                    if sessions > 0:
                        active_agents += 1
                    if has_memory:
                        memory_logged += 1

                    self._write_activity(
                        config.db_path, date, agent.id,
                        sessions, has_memory,
                    )

            # Step 2: Add ClawTeam-only agents not already listed in config.agents
            with tracer.span("Write ClawTeam-Only Agents") as ct_only_span:
                known_ids = {a.id for a in config.agents}
                new_ct_agents = [a for a in ct_agent_ids if a not in known_ids]

                for agent_id in new_ct_agents:
                    active_agents += 1
                    has_memory = self._check_memory_logged(
                        config.openclaw_home, agent_id, date,
                        clawteam_home=config.clawteam_home,
                    )
                    if has_memory:
                        memory_logged += 1
                    self._write_activity(config.db_path, date, agent_id, 1, has_memory)

                ct_only_span.set_attribute("clawteam_new_agents", len(new_ct_agents))

            total_agents = len(config.agents) + len(new_ct_agents)

            # Step 3: Compute metrics
            with tracer.span("Compute Metrics"):
                discipline = (
                    round(memory_logged / total_agents * 100, 1)
                    if total_agents > 0 else 0
                )

            root.set_attribute("active_agent_count", active_agents)
            root.set_attribute("memory_discipline", discipline)

        tracer.flush()
        return [
            Metric("active_agent_count", active_agents, unit="count", breakdown={
                "total_agents": total_agents,
                "active": active_agents,
            }),
            Metric("memory_discipline", discipline, unit="%", breakdown={
                "logged": memory_logged,
                "total": total_agents,
            }),
        ]

    def _count_agent_sessions(self, openclaw_home: Path, agent_id: str,
                              date: str, *,
                              clawteam_home: Path | None = None) -> int:
        """Count sessions for an agent on a given date across known layouts."""
        count = 0
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Layout 1: ~/.openclaw/sessions/agent:<id>:...
        sessions_dir = openclaw_home / "sessions"
        if sessions_dir.exists():
            for path in sessions_dir.iterdir():
                if not path.is_file():
                    continue
                if f"agent:{agent_id}:" not in path.name:
                    continue
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime).date()
                    if mtime == target_date:
                        count += 1
                except OSError:
                    continue

        # Layout 2: ~/.openclaw/agents/<id>/sessions/*
        agent_sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
        if agent_sessions_dir.exists():
            for path in agent_sessions_dir.iterdir():
                if not path.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime).date()
                    if mtime == target_date:
                        count += 1
                except OSError:
                    continue

        # Layout 3: ~/.clawteam/sessions/<agent_id>/*
        if clawteam_home is not None:
            ct_sessions = clawteam_home / "sessions" / agent_id
            if not ct_sessions.exists():
                # Also try stripping the "clawteam/" prefix virtual agents use
                raw_id = agent_id.removeprefix("clawteam/")
                ct_sessions = clawteam_home / "sessions" / raw_id
            if ct_sessions.exists():
                for path in ct_sessions.iterdir():
                    if not path.is_file():
                        continue
                    try:
                        mtime = datetime.fromtimestamp(path.stat().st_mtime).date()
                        if mtime == target_date:
                            count += 1
                    except OSError:
                        continue

        return count

    def _check_memory_logged(self, openclaw_home: Path, agent_id: str,
                             date: str, *,
                             clawteam_home: Path | None = None) -> bool:
        """Check if an agent has a memory file for the given date.

        Important: the shared main workspace memory file should only count for the
        main agent. Otherwise every configured agent appears to have logged memory.
        """
        possible_paths = [
            openclaw_home / "agents" / agent_id / "memory" / f"{date}.md",
            openclaw_home / "workspaces" / agent_id / "memory" / f"{date}.md",
        ]

        # Only the main agent may claim the shared workspace memory journal.
        if agent_id == "main":
            possible_paths += [
                openclaw_home / "workspace" / "memory" / f"{date}.md",
                openclaw_home / "workspace" / "memory" / f"{date}-*.md",
            ]

        # ClawTeam workspace memory layouts
        if clawteam_home is not None:
            raw_id = agent_id.removeprefix("clawteam/")
            possible_paths += [
                clawteam_home / "workspaces" / raw_id / "memory" / f"{date}.md",
                clawteam_home / "workspaces" / raw_id / "memory" / f"{date}-*.md",
            ]

        for path in possible_paths:
            if "*" in path.name:
                if path.parent.exists() and list(path.parent.glob(path.name)):
                    return True
            elif path.exists():
                return True

        return False

    def _write_activity(self, db_path: Path, date: str, agent_id: str,
                        session_count: int, memory_logged: bool) -> None:
        """Write agent activity to daily_agent_activity table."""
        db = sqlite3.connect(str(db_path))
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            """INSERT INTO daily_agent_activity
               (date, agent_id, session_count, memory_logged, created_at)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(date, agent_id) DO UPDATE SET
                   session_count = excluded.session_count,
                   memory_logged = excluded.memory_logged""",
            (date, agent_id, session_count, 1 if memory_logged else 0),
        )
        db.commit()
        db.close()

    def _scan_clawteam_active_agents(self, clawteam_home: Path, date: str) -> list[str]:
        """Scan ~/.clawteam/tasks to find agents active on a given date.

        Reads task-*.json files and checks updatedAt / startedAt / lockedAt fields.
        Returns a deduplicated list of agent (owner) IDs that were active on `date`.
        """
        import json

        if not clawteam_home.exists():
            return []

        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        active: set[str] = set()

        tasks_dir = clawteam_home / "tasks"
        if not tasks_dir.exists():
            return []

        for task_group in tasks_dir.iterdir():
            if not task_group.is_dir():
                continue
            for task_file in task_group.glob("task-*.json"):
                try:
                    with open(task_file, encoding="utf-8") as f:
                        data = json.load(f)

                    # Check if the task was active on the target date
                    ts_fields = ["updatedAt", "startedAt", "lockedAt", "createdAt"]
                    matched = False
                    for field in ts_fields:
                        ts_raw = data.get(field)
                        if ts_raw:
                            try:
                                ts = datetime.fromisoformat(
                                    ts_raw.replace("Z", "+00:00")
                                )
                                # Compare in local date
                                if ts.date() == target_date:
                                    matched = True
                                    break
                            except ValueError:
                                continue

                    # Also check file mtime as fallback
                    if not matched:
                        try:
                            mtime = datetime.fromtimestamp(task_file.stat().st_mtime).date()
                            if mtime == target_date:
                                matched = True
                        except OSError:
                            pass

                    if matched:
                        owner = data.get("owner")
                        locked_by = data.get("lockedBy")
                        # Use owner as agent ID; skip generic lock holders like "agent"
                        if owner and owner not in ("agent", ""):
                            active.add(owner)
                        elif locked_by and locked_by not in ("agent", ""):
                            active.add(locked_by)

                except (OSError, ValueError, KeyError):
                    continue

        return sorted(active)
