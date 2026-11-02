"""Run the API and Vite together from any working directory (Ctrl+C stops both)."""
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Brak npm: zainstaluj Node.js co najmniej 22.12; zalecane 24 lub 26 LTS.")
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT))
        processes.append(subprocess.Popen([npm, "run", "dev", "--", "--port", "5173", "--strictPort"], cwd=ROOT/"frontend"))
        if "--no-browser" not in sys.argv:
            webbrowser.open("http://127.0.0.1:5173")
        while all(p.poll() is None for p in processes):
            time.sleep(.5)
        raise SystemExit(next((p.returncode for p in processes if p.returncode), 0))
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
