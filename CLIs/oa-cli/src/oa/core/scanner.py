"""OpenClaw auto-detection — scans the local installation for agents, cron jobs, and sessions."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class AgentInfo:
    """Detected agent from OpenClaw installation."""
    id: str
    name: str
    last_active: str | None = None  # ISO timestamp


@dataclass
class CronJobInfo:
    """Detected cron job."""
    id: str
    name: str
    schedule: str
    enabled: bool = True


@dataclass
class ScanResult:
    """Result of scanning an OpenClaw installation."""
    openclaw_home: Path
    clawteam_home: Path = field(default_factory=lambda: Path.home() / ".clawteam")
    clawteam_found: bool = False
    agents: list[AgentInfo] = field(default_factory=list)
    cron_jobs: list[CronJobInfo] = field(default_factory=list)
    session_count: int = 0
    found: bool = False


class OpenClawScanner:
    """Scans ~/.openclaw and ~/.clawteam for agents, cron jobs, and sessions."""

    def __init__(self, openclaw_home: Path | None = None,
                 clawteam_home: Path | None = None):
        self.home = openclaw_home or Path.home() / ".openclaw"
        self.clawteam_home = clawteam_home or Path.home() / ".clawteam"

    def scan(self) -> ScanResult:
        """Run full scan and return results."""
        result = ScanResult(openclaw_home=self.home, clawteam_home=self.clawteam_home)

        if self.home.exists():
            result.found = True
            result.cron_jobs = self._scan_cron_jobs()
            result.agents = self._scan_agents()
            result.session_count = self._count_sessions()

        if self.clawteam_home.exists():
            result.clawteam_found = True
            clawteam_agents = self._scan_clawteam_agents()
            existing_ids = {a.id for a in result.agents}
            for agent in clawteam_agents:
                if agent.id not in existing_ids:
                    result.agents.append(agent)
                else:
                    # Merge last_active
                    existing = next(a for a in result.agents if a.id == agent.id)
                    if agent.last_active and (
                        not existing.last_active
                        or agent.last_active > existing.last_active
                    ):
                        existing.last_active = agent.last_active
            result.session_count += self._count_clawteam_sessions()

        return result

    def _scan_cron_jobs(self) -> list[CronJobInfo]:
        """Read cron job definitions from jobs.json."""
        jobs_file = self.home / "cron" / "jobs.json"
        if not jobs_file.exists():
            return []

        try:
            with open(jobs_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        jobs = data.get("jobs", [])
        result = []
        for job in jobs:
            schedule = job.get("schedule", {})
            schedule_str = schedule.get("expr", schedule.get("kind", "unknown"))
            result.append(CronJobInfo(
                id=job.get("id", "unknown"),
                name=job.get("name", job.get("id", "unknown")),
                schedule=schedule_str,
                enabled=job.get("enabled", True),
            ))
        return result

    def _scan_agents(self) -> list[AgentInfo]:
        """Detect agents from session directories and agent subdirectories."""
        agents: dict[str, AgentInfo] = {}

        def upsert_agent(agent_id: str, mtime_ts: float | None = None) -> None:
            if not agent_id:
                return
            mtime_iso = None
            if mtime_ts is not None:
                mtime_iso = datetime.fromtimestamp(mtime_ts).isoformat()
            existing = agents.get(agent_id)
            if not existing:
                agents[agent_id] = AgentInfo(id=agent_id, name=agent_id.upper(), last_active=mtime_iso)
                return
            if mtime_iso and (not existing.last_active or mtime_iso > existing.last_active):
                existing.last_active = mtime_iso

        # Pattern 1: top-level session files named like agent:<id>:...
        sessions_dir = self.home / "sessions"
        if sessions_dir.exists():
            for path in sessions_dir.iterdir():
                if not path.is_file():
                    continue
                try:
                    match = re.search(r"agent:([^:]+):", path.name)
                    if match:
                        upsert_agent(match.group(1), path.stat().st_mtime)
                except OSError:
                    continue

        # Pattern 2: OpenClaw agent directories: ~/.openclaw/agents/<id>/sessions/*
        agents_dir = self.home / "agents"
        if agents_dir.exists():
            for path in agents_dir.iterdir():
                if not path.is_dir():
                    continue
                agent_id = path.name
                upsert_agent(agent_id)
                sessions_subdir = path / "sessions"
                if sessions_subdir.exists():
                    for session_file in sessions_subdir.iterdir():
                        if not session_file.is_file():
                            continue
                        try:
                            upsert_agent(agent_id, session_file.stat().st_mtime)
                        except OSError:
                            continue

        return sorted(agents.values(), key=lambda a: a.id)

    def _count_sessions(self) -> int:
        """Count total session files across known OpenClaw layouts."""
        count = 0

        sessions_dir = self.home / "sessions"
        if sessions_dir.exists():
            count += sum(1 for f in sessions_dir.iterdir() if f.is_file())

        agents_dir = self.home / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                sessions_subdir = agent_dir / "sessions"
                if agent_dir.is_dir() and sessions_subdir.exists():
                    count += sum(1 for f in sessions_subdir.iterdir() if f.is_file())

        return count

    def _scan_clawteam_agents(self) -> list[AgentInfo]:
        """Detect agents from ~/.clawteam/tasks and ~/.clawteam/sessions."""
        agents: dict[str, AgentInfo] = {}

        def upsert(agent_id: str, mtime_ts: float | None = None) -> None:
            if not agent_id:
                return
            mtime_iso = None
            if mtime_ts is not None:
                mtime_iso = datetime.fromtimestamp(mtime_ts).isoformat()
            existing = agents.get(agent_id)
            if not existing:
                agents[agent_id] = AgentInfo(id=agent_id, name=agent_id.upper(), last_active=mtime_iso)
                return
            if mtime_iso and (not existing.last_active or mtime_iso > existing.last_active):
                existing.last_active = mtime_iso

        # Pattern 1: ~/.clawteam/tasks/<task-name>/task-*.json  →  owner field = agent
        tasks_dir = self.clawteam_home / "tasks"
        if tasks_dir.exists():
            for task_group in tasks_dir.iterdir():
                if not task_group.is_dir():
                    continue
                for task_file in task_group.glob("task-*.json"):
                    try:
                        import json
                        with open(task_file, encoding="utf-8") as f:
                            data = json.load(f)
                        owner = data.get("owner") or data.get("lockedBy")
                        if owner:
                            mtime = task_file.stat().st_mtime
                            upsert(owner, mtime)
                    except (OSError, ValueError):
                        continue

        # Pattern 2: ~/.clawteam/sessions/<task-name>/  →  treat task-name as agent-like group
        sessions_dir = self.clawteam_home / "sessions"
        if sessions_dir.exists():
            for group_dir in sessions_dir.iterdir():
                if group_dir.is_dir():
                    # Use the group dir name as a virtual agent ID
                    recent_mtime: float | None = None
                    for session_file in group_dir.iterdir():
                        if session_file.is_file():
                            try:
                                mtime = session_file.stat().st_mtime
                                if recent_mtime is None or mtime > recent_mtime:
                                    recent_mtime = mtime
                            except OSError:
                                continue
                    upsert(f"clawteam/{group_dir.name}", recent_mtime)

        return sorted(agents.values(), key=lambda a: a.id)

    def _count_clawteam_sessions(self) -> int:
        """Count session files in ~/.clawteam/sessions."""
        count = 0
        sessions_dir = self.clawteam_home / "sessions"
        if sessions_dir.exists():
            for group_dir in sessions_dir.iterdir():
                if group_dir.is_dir():
                    count += sum(1 for f in group_dir.iterdir() if f.is_file())
        return count
