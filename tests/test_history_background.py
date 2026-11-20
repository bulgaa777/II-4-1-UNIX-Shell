import os, pathlib, subprocess, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OSH = str(ROOT / 'osh')
PROMPT = 'osh> '
done = 0

def check(cond, msg):
    global done
    if not cond:
        raise AssertionError(msg)
    done += 1

def session(text):
    return subprocess.run([OSH], input=text, text=True, capture_output=True, timeout=8)

def run(cmd, cwd=None, env=None):
    return subprocess.run([OSH, '-c', cmd], cwd=cwd or ROOT, text=True,
                          capture_output=True, timeout=8, env=env)

def shown(out):
    """stdout lines without 'osh> ' prompts and without empty lines"""
    res = []
    for l in out.splitlines():
        while l.startswith(PROMPT):
            l = l[len(PROMPT):]
        if l:
            res.append(l)
    return res

# ---------- History (SUGGESTION-01): exact output instead of count('first') >= 2 ----------
M = 'HIST_MARK_7431'
r = session(f'echo {M}\n!!\nexit\n')
check(shown(r.stdout) == [M, f'echo {M}', M], 'history replay: command shown and executed again')

r = session('echo A1\necho B2\n!!\nexit\n')
check(shown(r.stdout) == ['A1', 'B2', 'echo B2', 'B2'], 'history replays the latest command')

r = session('echo X\n!!\n!!\nexit\n')
check(shown(r.stdout) == ['X', 'echo X', 'X', 'echo X', 'X'], 'history: !! twice')

r = session('echo ab | wc -c\n!!\nexit\n')
check(shown(r.stdout) == ['3', 'echo ab | wc -c', '3'], 'history replays a pipe')

r = session('echo W\n   \n  !!  \nexit\n')
check(shown(r.stdout) == ['W', 'echo W', 'W'], 'history survives blank line and padded !!')

r = session('no_such_cmd_h\n!!\nexit\n')
check(r.stderr.count('no_such_cmd_h') == 2, 'history replays a failed command')

r = session('!!\necho alive\nexit\n')
check('No commands in history' in r.stderr and shown(r.stdout) == ['alive'], 'empty history does not stop the shell')

# ---------- Background process: running -> completed / failed ----------
def read_events(path):
    rows = []
    for l in pathlib.Path(path).read_text().splitlines():
        ts, pid, ppid, state, cmd = l.split('\t', 4)
        rows.append((int(ts), int(pid), int(ppid), state, cmd))
    return rows

def proc_state(pid):
    try:
        return pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        return None

def background_case(cmd, final):
    with tempfile.TemporaryDirectory() as td:
        ev = os.path.join(td, 'events.tsv')
        p = subprocess.Popen([OSH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                             env={**os.environ, 'OSH_EVENTS': ev})
        p.stdin.write(cmd + '\n')
        p.stdin.flush()
        rows, end = [], time.time() + 5
        while not rows and time.time() < end:
            if os.path.exists(ev):
                rows = read_events(ev)
            time.sleep(0.05)
        check(rows and rows[0][3] == 'running', f'{cmd}: running event written')
        pid = rows[0][1]
        end = time.time() + 5
        while proc_state(pid) not in ('Z', None) and time.time() < end:   # wait until the child exited
            time.sleep(0.05)
        out, _ = p.communicate('echo shell_alive\nexit\n', timeout=8)     # next loop reaps it
        mine = [r for r in read_events(ev) if r[1] == pid]
        check([r[3] for r in mine] == ['running', final], f'{cmd}: states running -> {final}')
        check(all(r[2] == p.pid for r in mine), f'{cmd}: parent pid is the shell')
        check(mine[0][0] <= mine[1][0], f'{cmd}: timestamps in order')
        check(f'[background] PID {pid}' in out and 'shell_alive' in out, f'{cmd}: shell did not wait')

background_case('sleep 0.3 &', 'completed')
background_case("sh -c 'exit 3' &", 'failed')

for cmd, final in (('true', 'completed'), ('false', 'failed')):
    with tempfile.TemporaryDirectory() as td:
        ev = os.path.join(td, 'e.tsv')
        run(cmd, env={**os.environ, 'OSH_EVENTS': ev})
        check([r[3] for r in read_events(ev)] == ['running', final], f'foreground {cmd}: running -> {final}')

# ---------- Regression: pipe / redirection / history after the fixes ----------
with tempfile.TemporaryDirectory() as td:
    pathlib.Path(td, 'in.txt').write_text('b\na\nc\n')
    a = run('sort < in.txt | head -n 1 > out.txt', td)
    check(a.returncode == 0 and pathlib.Path(td, 'out.txt').read_text() == 'a\n', 'redirects on both ends of a pipe')
    a = run('cat < in.txt > copy.txt', td)
    check(a.returncode == 0 and pathlib.Path(td, 'copy.txt').read_text() == 'b\na\nc\n', 'input + output redirect')
    a = run('echo hi>glued.txt', td)
    check(pathlib.Path(td, 'glued.txt').read_text() == 'hi\n', 'redirect without spaces')
    a = run('echo "a > b" > q.txt', td)
    check(pathlib.Path(td, 'q.txt').read_text() == 'a > b\n' and not pathlib.Path(td, 'b').exists(), 'quoted > stays text')

a = run("echo 'x | y'")
check(a.returncode == 0 and a.stdout.strip() == 'x | y', 'quoted | stays text')
a = run('  echo   spaced   ')
check(a.stdout.strip() == 'spaced', 'padded command')
a = run('echo one | cat | wc -c')
check(a.returncode == 2 and 'Invalid pipe' in a.stderr, 'second pipe rejected')
a = run('echo hi & echo no')
check(a.returncode == 2 and 'must be last' in a.stderr, '& in the middle rejected')

print(f'PASS: {done} checks (history replay, background running->finished, pipe/redirect regression)')
