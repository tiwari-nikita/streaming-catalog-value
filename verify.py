"""One command: fetch Netflix's reports (hash-checked), rebuild everything, assert every claim.

    python verify.py
"""
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
STEPS = ["src/fetch_data.py", "src/build_panel.py", "src/analysis.py", "src/charts.py", "tests/test_claims.py"]

t0 = time.time()
for step in STEPS:
    s = time.time()
    r = subprocess.run([sys.executable, str(ROOT / step)], capture_output=True, text=True, cwd=str(ROOT))
    status = "ok  " if r.returncode == 0 else "FAIL"
    print("  {}  {:<24} {:>5.1f}s".format(status, step, time.time() - s))
    if step.startswith("tests"):
        print("\n".join("      " + l for l in r.stdout.strip().splitlines()))
    if r.returncode != 0:
        print((r.stderr or r.stdout)[-1500:])
        sys.exit(1)
print("\nAll results rebuilt and every claim verified in {:.0f}s.".format(time.time() - t0))
