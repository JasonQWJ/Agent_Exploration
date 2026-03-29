"""Tests for OpenClaw scanner."""
import json
import tempfile
from pathlib import Path

from oa.core.scanner import OpenClawScanner


class TestScanner:
    @staticmethod
    def _nonexistent_paths():
        """Return paths that definitely do not exist (avoids temp dir leakage)."""
        import uuid
        return (
            Path(f"/tmp/nonexistent-ct-{uuid.uuid4().hex[:8]}"),
            Path(f"/tmp/nonexistent-qc-{uuid.uuid4().hex[:8]}"),
        )

    def test_scan_missing_directory(self):
        no_ct, no_qc = self._nonexistent_paths()
        scanner = OpenClawScanner(
            openclaw_home=Path("/tmp/nonexistent-oa-test"),
            clawteam_home=no_ct,
            qclaw_home=no_qc,
        )
        result = scanner.scan()
        assert result.found is False
        assert result.qclaw_found is False
        assert len(result.agents) == 0
        assert len(result.cron_jobs) == 0

    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            scanner = OpenClawScanner(
                openclaw_home=Path(tmpdir),
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()
            assert result.found is True
            assert result.qclaw_found is False
            assert len(result.agents) == 0
            assert len(result.cron_jobs) == 0

    def test_scan_cron_jobs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            oc_home = Path(tmpdir)
            cron_dir = oc_home / "cron"
            cron_dir.mkdir()

            jobs = {
                "jobs": [
                    {
                        "id": "daily-collect",
                        "name": "Daily Collection",
                        "schedule": {"kind": "cron", "expr": "0 7 * * *"},
                        "enabled": True,
                    },
                    {
                        "id": "disabled-job",
                        "name": "Disabled",
                        "schedule": {"kind": "cron", "expr": "0 12 * * *"},
                        "enabled": False,
                    },
                ]
            }
            (cron_dir / "jobs.json").write_text(json.dumps(jobs))

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            assert len(result.cron_jobs) == 2
            assert result.cron_jobs[0].name == "Daily Collection"
            assert result.cron_jobs[0].enabled is True
            assert result.cron_jobs[1].enabled is False

    def test_scan_agents_from_agents_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            oc_home = Path(tmpdir)
            agents_dir = oc_home / "agents"
            (agents_dir / "researcher").mkdir(parents=True)
            (agents_dir / "writer").mkdir(parents=True)

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            agent_ids = [a.id for a in result.agents]
            assert "researcher" in agent_ids
            assert "writer" in agent_ids

    def test_scan_sessions_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            oc_home = Path(tmpdir)
            sessions_dir = oc_home / "sessions"
            sessions_dir.mkdir()

            for i in range(5):
                (sessions_dir / f"session-{i}.json").write_text("{}")

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()
            assert result.session_count == 5

    def test_scan_agents_from_agent_session_subdirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            oc_home = Path(tmpdir)
            agent_sessions = oc_home / "agents" / "main" / "sessions"
            agent_sessions.mkdir(parents=True)
            (agent_sessions / "abc.jsonl").write_text("{}")

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            agent_ids = [a.id for a in result.agents]
            assert "main" in agent_ids
            assert result.session_count == 1
            main_agent = next(a for a in result.agents if a.id == "main")
            assert main_agent.last_active is not None

    # ── QClaw-specific tests ────────────────────────────────────────────

    def test_qclaw_found_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, _ = self._nonexistent_paths()
            qc_home = Path(tmpdir) / "qclaw"
            (qc_home / "agents" / "main").mkdir(parents=True)

            scanner = OpenClawScanner(
                openclaw_home=Path("/tmp/nonexistent-oa-test"),
                clawteam_home=no_ct,
                qclaw_home=qc_home,
            )
            result = scanner.scan()
            assert result.qclaw_found is True

    def test_qclaw_agents_discovered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, _ = self._nonexistent_paths()
            qc_home = Path(tmpdir)
            agents_dir = qc_home / "agents"
            (agents_dir / "agent-alpha").mkdir(parents=True)
            (agents_dir / "agent-beta").mkdir(parents=True)

            scanner = OpenClawScanner(
                openclaw_home=Path("/tmp/nonexistent-oa-test"),
                clawteam_home=no_ct,
                qclaw_home=qc_home,
            )
            result = scanner.scan()

            agent_ids = [a.id for a in result.agents]
            assert "agent-alpha" in agent_ids
            assert "agent-beta" in agent_ids

    def test_qclaw_sessions_counted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, _ = self._nonexistent_paths()
            qc_home = Path(tmpdir)
            sessions_dir = qc_home / "agents" / "main" / "sessions"
            sessions_dir.mkdir(parents=True)
            for i in range(3):
                (sessions_dir / f"session-{i}.jsonl").write_text("{}")

            scanner = OpenClawScanner(
                openclaw_home=Path("/tmp/nonexistent-oa-test"),
                clawteam_home=no_ct,
                qclaw_home=qc_home,
            )
            result = scanner.scan()
            assert result.session_count == 3

    def test_qclaw_and_openclaw_agents_merged(self):
        """Agents found in both sources should be merged, not duplicated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, _ = self._nonexistent_paths()
            oc_home = Path(tmpdir)
            qc_home = oc_home / "qclaw"
            qc_home.mkdir()

            (oc_home / "agents" / "shared-bot").mkdir(parents=True)
            (qc_home / "agents" / "shared-bot").mkdir(parents=True)
            (qc_home / "agents" / "qclaw-only").mkdir(parents=True)

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=no_ct,
                qclaw_home=qc_home,
            )
            result = scanner.scan()

            agent_ids = [a.id for a in result.agents]
            assert agent_ids.count("shared-bot") == 1  # not duplicated
            assert "shared-bot" in agent_ids
            assert "qclaw-only" in agent_ids

    # ── ClawTeam-specific tests ──────────────────────────────────────────

    def test_clawteam_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_ct, no_qc = self._nonexistent_paths()
            scanner = OpenClawScanner(
                openclaw_home=Path(tmpdir),
                clawteam_home=no_ct,
                qclaw_home=no_qc,
            )
            result = scanner.scan()
            assert result.clawteam_found is False

    def test_clawteam_agents_from_tasks(self):
        with tempfile.TemporaryDirectory() as oc_dir, \
             tempfile.TemporaryDirectory() as ct_dir:
            no_qc, _ = self._nonexistent_paths()
            ct_home = Path(ct_dir)
            tasks_dir = ct_home / "tasks" / "my-task"
            tasks_dir.mkdir(parents=True)

            task_data = {
                "id": "abc123",
                "subject": "Do something",
                "status": "in_progress",
                "owner": "coder",
                "lockedBy": "agent",
            }
            (tasks_dir / "task-abc123.json").write_text(json.dumps(task_data))

            scanner = OpenClawScanner(
                openclaw_home=Path(oc_dir),
                clawteam_home=ct_home,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            assert result.clawteam_found is True
            agent_ids = [a.id for a in result.agents]
            assert "coder" in agent_ids

    def test_clawteam_sessions_counted(self):
        with tempfile.TemporaryDirectory() as oc_dir, \
             tempfile.TemporaryDirectory() as ct_dir:
            no_qc, _ = self._nonexistent_paths()
            ct_home = Path(ct_dir)
            task_sessions = ct_home / "sessions" / "worldmodel-deep"
            task_sessions.mkdir(parents=True)
            (task_sessions / "agent.json").write_text("{}")

            scanner = OpenClawScanner(
                openclaw_home=Path(oc_dir),
                clawteam_home=ct_home,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            assert result.clawteam_found is True
            assert result.session_count == 1
            agent_ids = [a.id for a in result.agents]
            assert "clawteam/worldmodel-deep" in agent_ids

    def test_clawteam_merges_with_openclaw_agents(self):
        """Agents in both sources should be merged, not duplicated."""
        with tempfile.TemporaryDirectory() as oc_dir, \
             tempfile.TemporaryDirectory() as ct_dir:
            no_qc, _ = self._nonexistent_paths()
            oc_home = Path(oc_dir)
            ct_home = Path(ct_dir)

            (oc_home / "agents" / "shared-bot").mkdir(parents=True)

            tasks_dir = ct_home / "tasks" / "my-task"
            tasks_dir.mkdir(parents=True)
            (tasks_dir / "task-x.json").write_text(json.dumps({"owner": "shared-bot"}))

            scanner = OpenClawScanner(
                openclaw_home=oc_home,
                clawteam_home=ct_home,
                qclaw_home=no_qc,
            )
            result = scanner.scan()

            agent_ids = [a.id for a in result.agents]
            assert agent_ids.count("shared-bot") == 1  # not duplicated
