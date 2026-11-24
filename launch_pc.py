"""Windows launcher. --kiosk enables v28's optional return-to-program screen."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kiosk", action="store_true")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    env = os.environ.copy()
    env.pop("ANTI_FINGER_LAUNCHER", None)
    if args.kiosk:
        env["ANTI_FINGER_LAUNCHER"] = "1"
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    while True:
        code = subprocess.call([sys.executable, str(folder / "main.py")], cwd=folder,
                               env=env, creationflags=flags)
        if not args.kiosk:
            return code
        if code == 0:  # user selected Back in the in-app relaunch screen
            continue
        if code == 1:  # user selected Close
            return 0
        fallback = subprocess.call([sys.executable, str(folder / "relaunch.py")], cwd=folder,
                                   env=env, creationflags=flags)
        if fallback != 0:
            return code


if __name__ == "__main__":
    sys.exit(main())
