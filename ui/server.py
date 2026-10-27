
"""UNIX Shell Explorer - Local server."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import re
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
EVENTS = Path(tempfile.gettempdir()) / f"osh_events_{os.getpid()}.tsv"

HISTORY = []
LOCK = threading.Lock()
BACKGROUND = {}
BG_PATTERN = re.compile(r"\[background\] PID (\d+)")


def is_running(pid):
    """Check if a process is still running."""
    try:
        check = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True,
            text=True,
            timeout=2
        )

        state = check.stdout.strip()

        return (
            check.returncode == 0
            and bool(state)
            and not state.startswith("Z")
        )

    except (OSError, subprocess.TimeoutExpired):
        return None


def get_events():
    latest = {}

    if EVENTS.exists():
        lines = EVENTS.read_text(errors="replace").splitlines()

        for line in lines:
            parts = line.split("\t", 4)

            if len(parts) == 5:
                ts, pid, ppid, state, cmd = parts

                latest[pid] = {
                    "pid": pid,
                    "ppid": ppid,
                    "state": state,
                    "command": cmd,
                    "time": ts
                }

    for pid, known_state in list(BACKGROUND.items()):
        entry = latest.get(str(pid))

        if entry is None:
            continue

        if known_state == "running":
            alive = is_running(pid)

            if alive is False:
                BACKGROUND[pid] = "finished"

        if entry["state"] == "running":
            entry["state"] = BACKGROUND[pid]

    return list(latest.values())[-50:]


class Handler(BaseHTTPRequestHandler):

    def reply(self, obj, code=200):
        data = json.dumps(
            obj,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        route = urlparse(self.path).path

        if route == "/":
            data = (ROOT / "ui" / "index.html").read_bytes()

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif route == "/api/events":
            with LOCK:
                data = {
                    "events": get_events(),
                    "history": HISTORY[-15:]
                }

            self.reply(data)

        else:
            self.reply({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/api/run":
            return self.reply({"error": "Not found"}, 404)

        try:
            size = int(
                self.headers.get("Content-Length", "0")
            )

            if size < 1 or size > 8192:
                return self.reply(
                    {"error": "Invalid input size"}, 413
                )

            data = json.loads(self.rfile.read(size))
            cmd = str(data.get("command", "")).strip()

            if not cmd or len(cmd) > 1000:
                return self.reply(
                    {"error": "Enter a valid command"}, 400
                )

            with LOCK:
                if cmd == "!!":
                    if not HISTORY:
                        return self.reply(
                            {"error": "No commands in history"}, 400
                        )

                    cmd = HISTORY[-1]

                if cmd == "exit":
                    return self.reply(
                        {"error": "Use Reset view instead"}, 400
                    )

                HISTORY.append(cmd)

            env = dict(
                os.environ,
                OSH_EVENTS=str(EVENTS)
            )

            try:
                run = subprocess.run(
                    [str(ROOT / "osh"), "-c", cmd],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=6
                )

                match = BG_PATTERN.search(run.stdout)

                if match and run.returncode == 0:
                    with LOCK:
                        BACKGROUND[int(match.group(1))] = "running"

                self.reply({
                    "command": cmd,
                    "stdout": run.stdout[:20000],
                    "stderr": run.stderr[:20000],
                    "code": run.returncode
                })

            except subprocess.TimeoutExpired:
                self.reply(
                    {"error": "Command timed out"}, 408
                )

        except (ValueError, KeyError, json.JSONDecodeError) as err:
            self.reply({"error": str(err)}, 400)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if not (ROOT / "osh").exists():
        raise SystemExit("Run make first")

    print("Open http://127.0.0.1:8765")

    try:
        ThreadingHTTPServer(
            ("127.0.0.1", 8765),
            Handler
        ).serve_forever()

    finally:
        EVENTS.unlink(missing_ok=True)
