FROM python:3.11-slim

WORKDIR /app

COPY dist/ /tmp/dist/
RUN python -m pip install --no-cache-dir /tmp/dist/oa_cli-0.1.4-py3-none-any.whl && rm -rf /tmp/dist

WORKDIR /work

CMD ["bash", "-lc", "python - <<'PY'\nfrom pathlib import Path\nfrom oa.core.scanner import OpenClawScanner\nfrom oa.core.config import ProjectConfig\nscan = OpenClawScanner(Path('/data/openclaw'), clawteam_home=Path('/data/clawteam')).scan()\nconfig = ProjectConfig.from_scan(scan)\nconfig.openclaw_home = Path('/data/openclaw')\nconfig.clawteam_home = Path('/data/clawteam')\nconfig.db_path = Path('data/monitor.db')\nconfig.save(Path('/work/config.yaml'))\nprint('Detected agents:', ', '.join(a.id for a in config.agents) or '(none)')\nPY\noa collect --config /work/config.yaml && exec oa serve --config /work/config.yaml --host 0.0.0.0 --port 3460 --no-open"]
