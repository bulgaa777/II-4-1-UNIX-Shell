import pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
files = sorted(ROOT.glob('tests/test_*.py'))
rows, total, failed = [], 0, 0

for f in files:
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, str(f)], cwd=ROOT, text=True, capture_output=True, timeout=120)
    ok = r.returncode == 0
    m = re.search(r'PASS: (\d+)', r.stdout)
    n = int(m.group(1)) if m else (1 if ok else 0)
    total += n if ok else 0
    failed += 0 if ok else 1
    rows.append((f.name, 'PASS' if ok else 'FAIL', n, time.monotonic() - t0))
    if not ok:
        print(f'--- {f.name} failed ---\n{r.stdout}{r.stderr}')

print(f"{'file':32} {'result':7} {'checks':>6} {'time':>7}")
for name, res, n, sec in rows:
    print(f'{name:32} {res:7} {n:>6} {sec:6.2f}s')
print(f"{'TOTAL':32} {'FAIL' if failed else 'PASS':7} {total:>6}")
sys.exit(1 if failed else 0)
