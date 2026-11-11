"""Wait until r1 has booted and ws1 and srv1 accept SSH logins."""
import sys
import time
import pathlib

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

deadline = time.time() + 240
while True:
    pending = [n for n in lab.NETWORK + lab.MACHINES if not lab.ready(n)]
    if not pending:
        break
    if time.time() > deadline:
        sys.exit(f"these didn't come up in 4 minutes: {', '.join(pending)}   (docker logs <name> says why)")
    print(f"  waiting for {', '.join(pending)} ...", flush=True)
    time.sleep(3)
print("\n  the network is up: ws1, r1 and srv1. Start with task 1.1, in a terminal of your own.\n")
