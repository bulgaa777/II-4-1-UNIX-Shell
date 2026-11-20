
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8765/api/run"

server = subprocess.Popen(
    [sys.executable, str(ROOT / "ui/server.py")],
    cwd=ROOT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

try:
    # Wait for local server to start
    for _ in range(30):
        try:
            urllib.request.urlopen(
                "http://127.0.0.1:8765", timeout=1
            ).close()
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise AssertionError("Server did not start")

    request = urllib.request.Request(
        URL,
        data=json.dumps({"command": "sleep 7 &"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    start = time.monotonic()

    with urllib.request.urlopen(request, timeout=3) as response:
        result = json.load(response)
        assert response.status == 200

    elapsed = time.monotonic() - start

    assert elapsed < 3, f"Background response took {elapsed:.2f}s"
    assert result["code"] == 0
    assert "[background] PID" in result["stdout"]

    print(f"PASS: background HTTP test ({elapsed:.3f}s)")

finally:
    server.terminate()
    server.wait(timeout=5)
