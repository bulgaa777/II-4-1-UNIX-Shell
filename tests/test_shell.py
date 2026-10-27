import subprocess, tempfile, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run(cmd, cwd=None):
 return subprocess.run([str(ROOT/'osh'),'-c',cmd],cwd=cwd or ROOT,text=True,capture_output=True,timeout=8)
def check(cond, msg):
 if not cond:raise AssertionError(msg)
a=run('echo hello');check(a.returncode==0 and a.stdout.strip()=='hello','echo')
a=run('echo hello | wc -c');check(a.returncode==0 and a.stdout.strip()=='6','pipe')
with tempfile.TemporaryDirectory() as td:
 a=run('echo sample > output.txt',td);check(a.returncode==0,'output redirect')
 a=run('cat < output.txt',td);check(a.stdout.strip()=='sample','input redirect')
a=run('!!');check('No commands in history' in a.stderr,'empty history')
a=run('echo hi |');check(a.returncode!=0,'invalid pipe')
a=run('cat < /this_file_does_not_exist_123');check(a.returncode!=0,'missing file')
a=subprocess.run([str(ROOT/'osh')],input='echo first\n!!\nexit\n',text=True,capture_output=True,timeout=8)
check(a.stdout.count('first')>=2,'history replay')
print('PASS: 8 tests (echo, pipe, input/output redirection, history, errors)')
