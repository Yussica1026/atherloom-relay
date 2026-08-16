import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


def wait_for_http(url: str, process: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Wrangler exited before readiness ({process.returncode})")
        try:
            urllib.request.urlopen(url, timeout=1)
        except urllib.error.HTTPError:
            return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.4)
        else:
            return
    raise RuntimeError("Wrangler did not become HTTP-ready in time")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9797
    base = f"http://127.0.0.1:{port}"
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "dev", "--", "--port", str(port), "--var", "ADMIN_SECRET:local-integration-secret-123456"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    try:
        wait_for_http(base, process)
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "relay_integration.py"), base])
        raise SystemExit(result.returncode)
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
