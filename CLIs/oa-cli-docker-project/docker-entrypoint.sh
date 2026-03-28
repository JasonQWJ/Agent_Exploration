#!/usr/bin/env bash
set -euo pipefail
python -m pip install --no-cache-dir /work/dist/oa_cli-0.1.4-py3-none-any.whl click rich pyyaml >/tmp/oa-pip.log 2>&1 || { cat /tmp/oa-pip.log; exit 1; }
cd /work
python - <<'PY'
from pathlib import Path
from oa.core.scanner import OpenClawScanner
from oa.core.config import ProjectConfig
scan = OpenClawScanner(Path('/data/openclaw'), clawteam_home=Path('/data/clawteam')).scan()
config = ProjectConfig.from_scan(scan)
config.openclaw_home = Path('/data/openclaw')
config.clawteam_home = Path('/data/clawteam')
config.db_path = Path('data/monitor.db')
config.save(Path('/work/config.yaml'))
print('Detected agents:', ', '.join(a.id for a in config.agents) or '(none)')
PY
oa collect --config /work/config.yaml

# Start background collector loop (every 4 hours)
(
  while true; do
    sleep 14400
    echo "$(date) - Running scheduled collection..."
    oa collect --config /work/config.yaml
  done
) &

python - <<'PY'
from pathlib import Path
p = Path('/usr/local/lib/python3.11/site-packages/oa/server.py')
s = p.read_text()
old = 'server = HTTPServer(("127.0.0.1", port), OAHandler)'
new = 'server = HTTPServer(("0.0.0.0", port), OAHandler)'
if old in s:
    p.write_text(s.replace(old, new))
    print('Patched serve bind address to 0.0.0.0')
PY
exec oa serve --config /work/config.yaml --port 3460 --no-open
