# /// script
# requires-python = ">=3.11"
# ///
"""Lance l'API (port 8000) et l'interface (port 5173) ensemble.

    uv run lancer.py              le portail, normalement
    uv run lancer.py --instable   réseau lent et capricieux, pour éprouver l'interface

Ctrl+C arrête les deux.
"""
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent


def arreter(_signal, _cadre):
    raise KeyboardInterrupt


def main() -> None:
    signal.signal(signal.SIGTERM, arreter)
    uv, npm = shutil.which("uv"), shutil.which("npm")
    if not uv:
        sys.exit("uv introuvable : voir https://docs.astral.sh/uv/")
    if not npm:
        sys.exit("npm introuvable : installer Node.js 20 ou plus")

    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)  # l'API utilise son propre environnement, api/.venv
    if "--instable" in sys.argv:
        env["PORTAIL_RESEAU_INSTABLE"] = "1"
        print("Mode instable : la liste répond en 150 à 900 ms et échoue une fois sur huit.")

    if not (RACINE / "web" / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=RACINE / "web", check=True)

    api = subprocess.Popen([uv, "run", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
                           cwd=RACINE / "api", env=env)
    web = subprocess.Popen([npm, "run", "dev"], cwd=RACINE / "web", env=env)
    print("\nPortail : http://localhost:5173    API : http://localhost:8000/docs\n")
    try:
        while api.poll() is None and web.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for processus in (api, web):
            if processus.poll() is None:
                # SIGINT, comme Ctrl+C : uv le transmet au serveur qu'il a lancé.
                if os.name == "posix":
                    processus.send_signal(signal.SIGINT)
                else:
                    processus.terminate()
        for processus in (api, web):
            try:
                processus.wait(timeout=5)
            except subprocess.TimeoutExpired:
                processus.kill()


if __name__ == "__main__":
    main()
