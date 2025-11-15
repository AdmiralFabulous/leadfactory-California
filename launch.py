# launch.py

import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent


def start_process(args: list) -> subprocess.Popen:
    """
    Start a subprocess in the project root and return the handle.
    """
    return subprocess.Popen(
        args,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> None:
    processes: List[subprocess.Popen] = []

    # 1. Start main orchestrator in auto mode
    print("[launcher] Starting main orchestrator: python main.py --run-once")
    processes.append(start_process([sys.executable, "main.py", "--run-once"]))

    # 2. Start the dashboard
    print("[launcher] Starting dashboard: python dashboard.py")
    processes.append(start_process([sys.executable, "dashboard.py"]))

    # 3. Give the dashboard a moment to come up, then open browser
    time.sleep(5)
    url = "http://127.0.0.1:5000"
    print(f"[launcher] Opening dashboard at {url}")
    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"[launcher] Could not open browser automatically: {exc}")

    print("[launcher] LeadFactory is running. Press Ctrl+C to stop.")

    try:
        # Wait on child processes; if any exits, we just print their output.
        while True:
            alive = False
            for proc in list(processes):
                ret = proc.poll()
                if ret is None:
                    alive = True
                    continue
                print(f"[launcher] Process {proc.args} exited with code {ret}")
                processes.remove(proc)
            if not alive:
                print("[launcher] All processes have exited. Shutting down.")
                break
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[launcher] Ctrl+C received. Terminating child processes...")
        for proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        time.sleep(2)
        for proc in processes:
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
        print("[launcher] Shutdown complete.")


if __name__ == "__main__":
    main()
