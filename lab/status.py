"""make status · what's running, and where to start.

The dev container runs this when the folder opens. It only reads. Safe to run any time.
"""
import os
import shutil
import sys
import time
import pathlib

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

GUIDE = "https://networkdoodles.com/labs/linux-cli-101"
TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
G, R, Y, D, B, X = (("\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m") if TTY else ("",) * 6)
WHAT = {"ws1": "a Linux workstation (chapters 4, 6 and 8)", "srv1": "a Linux server (chapters 6 and 8)",
        "r1": "the router between them"}


def row(ok, name, value):
    mark = f"{G}✓{X}" if ok else (f"{Y}·{X}" if ok is None else f"{R}✗{X}")
    print(f"  {mark} {name:<10} {value}")


def main():
    wait = "--wait" in sys.argv
    print(f"\n{B}Linux and the command line 101{X}   {D}{GUIDE}{X}\n")
    row(True, "codespace", "your own terminal: most of chapters 1 to 7 happen there")
    if not shutil.which("docker"):
        row(False, "docker", "not found: open the lab in its dev container (Codespaces does this for you)")
        return 1
    deadline = time.time() + (300 if wait else 0)
    while True:
        up = {n: lab.ready(n) for n in lab.NETWORK + lab.MACHINES}
        if all(up.values()) or time.time() >= deadline:
            break
        print(f"  {D}starting: {', '.join(n for n, ok in up.items() if not ok)} ...{X}", flush=True)
        time.sleep(5)
    for n in ("ws1", "r1", "srv1"):
        row(up[n], n, WHAT[n] if up[n] else f"{WHAT[n]}: not running yet (make up starts it)")
    if all(up.values()):
        print(f"\n  {G}Ready.{X} Open a terminal of your own ({B}Ctrl+`{X}) and follow task 1.1.\n")
        return 0
    print(f"\n  Not everything is up. {B}make up{X} starts the network (under a minute).\n")
    return 1


sys.exit(main())
