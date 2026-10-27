"""Local demo only. Runs user-entered commands; never expose to the internet."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, subprocess, os, tempfile, threading
ROOT=Path(__file__).resolve().parents[1]
EVENTS=Path(tempfile.gettempdir())/f'osh_events_{os.getpid()}.tsv'
HISTORY=[]
LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def reply(self,obj,code=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if urlparse(self.path).path=='/':
   b=(ROOT/'ui'/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  elif urlparse(self.path).path=='/api/events':
   entries={}
   if EVENTS.exists():
    for line in EVENTS.read_text(errors='replace').splitlines():
     parts=line.split('\t',4)
     if len(parts)==5:
      ts,pid,ppid,state,cmd=parts;entries[pid]={'pid':pid,'ppid':ppid,'state':state,'command':cmd,'time':ts}
   self.reply({'events':list(entries.values())[-50:],'history':HISTORY[-15:]})
  else:self.reply({'error':'Not found'},404)
 def do_POST(self):
  if self.path!='/api/run':return self.reply({'error':'Not found'},404)
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>8192:return self.reply({'error':'Input too large'},413)
   data=json.loads(self.rfile.read(size));cmd=str(data.get('command','')).strip()
   if not cmd:return self.reply({'error':'Enter a command'},400)
   if len(cmd)>1000:return self.reply({'error':'Command too long'},400)
   with LOCK:
    if cmd=='!!':
     if not HISTORY:return self.reply({'error':'No commands in history.'},400)
     cmd=HISTORY[-1]
    if cmd=='exit':return self.reply({'error':'Use Reset to clear visualization; exit applies to CLI.'},400)
    HISTORY.append(cmd)
   env=dict(os.environ,OSH_EVENTS=str(EVENTS))
   try:
    proc=subprocess.run([str(ROOT/'osh'),'-c',cmd],cwd=ROOT,env=env,text=True,capture_output=True,timeout=6)
    self.reply({'command':cmd,'stdout':proc.stdout[:20000],'stderr':proc.stderr[:20000],'code':proc.returncode})
   except subprocess.TimeoutExpired:self.reply({'command':cmd,'error':'Timed out after 6 seconds; use short commands.'},408)
  except (ValueError,KeyError,json.JSONDecodeError) as e:self.reply({'error':str(e)},400)
 def log_message(self,*args):pass
if __name__=='__main__':
 if not (ROOT/'osh').exists():raise SystemExit('Run make first')
 print('Open http://127.0.0.1:8765  (local-only demo)')
 try:ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
 finally:EVENTS.unlink(missing_ok=True)
