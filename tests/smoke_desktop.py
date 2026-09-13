#!/usr/bin/env python3
"""Optional live Hyprland/Foot smoke test; opens a fullscreen window briefly."""
import json
from pathlib import Path
import subprocess
import sys
import time

app = Path(__file__).resolve().parents[1] / 'bob_screensaver.py'
process = subprocess.Popen([sys.executable, str(app), '--launch', '--terminal', 'foot',
                            '--once', '--interval', '1'], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
try:
    deadline = time.monotonic() + 8
    found = None
    while time.monotonic() < deadline and process.poll() is None:
        clients = json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))
        found = next((c for c in clients if c.get('class') == 'subgenius-screensaver'), None)
        if found and found.get('fullscreen'):
            break
        time.sleep(0.1)
    output, error = process.communicate(timeout=10)
    assert found and found.get('fullscreen'), 'No fullscreen app window detected'
    assert process.returncode == 0, error
    print('PASS: actual fullscreen window', found['size'], 'app-id', found['class'])
    print('PASS: completed one rotation, launcher exit', process.returncode)
    if error:
        print('Terminal diagnostics:', error.strip())
finally:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
