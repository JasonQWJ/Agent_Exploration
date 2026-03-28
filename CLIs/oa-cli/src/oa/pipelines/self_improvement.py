"""G3: System Self-Improving Pipeline — tracks agent team growth and improvement."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .base import Metric, Pipeline

if TYPE_CHECKING:
    from oa.core.config import ProjectConfig


class SelfImprovingPipeline(Pipeline):
    """Built-in pipeline: measures whether the agent team is improving over time.

    Tracks:
    - issues_resolved:  Count of closed/detected→fixed issues in ClawTeam tasks
    - skills_added:     New skills installed in OpenClaw
    - memory_entries:   Memory files written (knowledge capture)
    - self_improvement_score: Composite 0–100 score
    """

    goal_id = "self_improvement"

    def collect(self, date: str, config: "ProjectConfig") -> list[Metric]:
        from oa.core.tracing import Tracer

        tracer = Tracer(service="g3_self_improving", db_path=config.db_path)

        with tracer.span("G3: Self Improving", {"goal": "G3", "date": date}) as root:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()

            # Step 1: Issues resolved from ClawTeam tasks
            with tracer.span("Scan Issues Resolved") as span:
                issues_resolved = self._count_resolved_issues(config.clawteam_home, target_date)
                span.set_attribute("issues_resolved", issues_resolved)

            # Step 2: New skills installed
            with tracer.span("Scan Skills Installed") as span:
                skills_added = self._count_new_skills(config.openclaw_home, target_date)
                span.set_attribute("skills_added", skills_added)

            # Step 3: Memory entries written
            with tracer.span("Scan Memory Entries") as span:
                memory_entries = self._count_memory_entries(
                    config.openclaw_home, config.clawteam_home, target_date
                )
                span.set_attribute("memory_entries", memory_entries)

            # Step 4: Composite score (0–100)
            with tracer.span("Compute Score"):
                # Normalize: 3+ issues = good, 1+ skill = good, 5+ memory = good
                issue_score = min(100, issues_resolved * 33)
                skill_score = min(100, skills_added * 50)
                memory_score = min(100, (memory_entries / 5) * 100)
                composite = round((issue_score + skill_score + memory_score) / 3, 1)

            root.set_attribute("issues_resolved", issues_resolved)
            root.set_attribute("skills_added", skills_added)
            root.set_attribute("memory_entries", memory_entries)
            root.set_attribute("self_improvement_score", composite)

        tracer.flush()

        return [
            Metric(
                "self_improvement_score",
                composite,
                unit="%",
                breakdown={
                    "issues_resolved": issues_resolved,
                    "skills_added": skills_added,
                    "memory_entries": memory_entries,
                    "issue_score": issue_score,
                    "skill_score": skill_score,
                    "memory_score": memory_score,
                },
            ),
            Metric("issues_resolved", float(issues_resolved), unit="count"),
            Metric("skills_added", float(skills_added), unit="count"),
            Metric("memory_entries", float(memory_entries), unit="count"),
        ]

    # ─── Issues ────────────────────────────────────────────────────────────────

    def _count_resolved_issues(self, clawteam_home: Path, target_date) -> int:
        """Count ClawTeam tasks with status=done/closed resolved on target_date."""
        if not clawteam_home.exists():
            return 0

        count = 0
        tasks_dir = clawteam_home / "tasks"
        if not tasks_dir.exists():
            return 0

        for task_group in tasks_dir.iterdir():
            if not task_group.is_dir():
                continue
            for task_file in task_group.glob("task-*.json"):
                try:
                    mtime = datetime.fromtimestamp(task_file.stat().st_mtime).date()
                    if mtime != target_date:
                        continue
                    with open(task_file, encoding="utf-8") as f:
                        data = json.load(f)
                    status = (data.get("status") or "").lower()
                    resolution = data.get("resolution") or ""
                    # Consider resolved if status indicates done/closed or has a resolution note
                    if status in ("done", "completed", "closed", "fixed", "resolved"):
                        count += 1
                    elif resolution and target_date:
                        # Also count tasks that got a resolution note today
                        resolved_at = data.get("resolvedAt") or data.get("closedAt")
                        if resolved_at:
                            try:
                                dt = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                                if dt.date() == target_date:
                                    count += 1
                            except ValueError:
                                pass
                except (OSError, ValueError, KeyError):
                    continue

        return count

    # ─── Skills ───────────────────────────────────────────────────────────────

    def _count_new_skills(self, openclaw_home: Path, target_date) -> int:
        """Count newly created skill directories in OpenClaw skill paths."""
        skill_dirs = [
            openclaw_home / "config" / "skills",
            openclaw_home / "skills",
        ]
        # Also check workspace skills
        workspace_home = openclaw_home / "workspace"
        if workspace_home.exists():
            for sub in workspace_home.iterdir():
                if sub.is_dir():
                    skill_dirs.append(sub / "skills")

        count = 0
        for base in skill_dirs:
            if not base.exists():
                continue
            for item in base.iterdir():
                if not item.is_dir() and not item.suffix == ".md":
                    continue
                try:
                    # Check creation time via stat
                    ctime = datetime.fromtimestamp(item.stat().st_ctime).date()
                    if ctime == target_date:
                        count += 1
                except OSError:
                    continue

        return count

    # ─── Memory ────────────────────────────────────────────────────────────────

    def _count_memory_entries(
        self, openclaw_home: Path, clawteam_home: Path, target_date
    ) -> int:
        """Count memory .md files with today's date in filename or mtime."""
        count = 0
        date_prefix = target_date.strftime("%Y-%m-%d")

        for base in [openclaw_home, clawteam_home]:
            if not base.exists():
                continue

            # Search in known memory locations
            for loc in [base / "workspace" / "memory", base / "workspaces"]:
                if not loc.exists():
                    continue
                for sub in loc.iterdir():
                    if not sub.is_dir():
                        continue
                    for memory_dir in [sub / "memory", sub]:
                        count += self._count_in_dir(memory_dir, date_prefix, target_date)

        return count

    def _count_in_dir(self, directory: Path, date_prefix: str, target_date) -> int:
        """Helper to count matching files in a directory. Returns count."""
        if not directory.exists():
            return 0
        count = 0
        for item in directory.iterdir():
            if not item.is_file() or item.suffix not in (".md", ".txt"):
                continue
            if item.name.startswith(date_prefix):
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime).date()
                    if mtime == target_date:
                        count += 1
                except OSError:
                    pass
        return count
