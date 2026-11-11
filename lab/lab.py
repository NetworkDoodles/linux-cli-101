"""Small helpers the checker, the solver and the status page share."""
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "lab" / ".state"
MACHINES = ["ws1", "srv1"]          # Debian, with OpenSSH: user netops
NETWORK = ["r1"]                    # CapeOS Bolt: an IOS-style CLI
MGMT = {"r1": "172.80.102.2", "ws1": "172.80.102.11", "srv1": "172.80.102.12"}
HOME = pathlib.Path(os.path.expanduser("~"))


def run(args, timeout=20, input=None, env=None, cwd=None):
    """Run a command here, in the codespace; return (exit code, output)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input, env=env, cwd=cwd)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 127, str(e)


def sh(node, cmd, timeout=20, user=None):
    """Run a shell command on ws1 or srv1 (as root, or as user); return (exit code, output)."""
    args = ["docker", "exec"] + (["-u", user, "-w", f"/home/{user}"] if user else []) + [node, "sh", "-c", cmd]
    return run(args, timeout)


def show(node, cmd, timeout=20):
    """Run a CLI command on r1; return its output ('' if it can't)."""
    code, out = run(["docker", "exec", "-i", node, "capeos-cli", "-c", cmd], timeout)
    return out if code == 0 else ""


def config(node, *lines):
    text = "\n".join(["configure terminal", *lines, "end", ""])
    return run(["docker", "exec", "-i", node, "capeos-cli"], 30, input=text)[1]


def running(node):
    return run(["docker", "inspect", "-f", "{{.State.Running}}", node])[1] == "true"


def ready(node):
    if not running(node):
        return False
    if node in NETWORK:
        return sh(node, "test -e /run/capeos/ready")[0] == 0
    return sh(node, "pgrep -x sshd >/dev/null")[0] == 0


def ssh(host, cmd="true", timeout=15, opts=()):
    """ssh from the codespace the way the learner does, never asking for anything (BatchMode)."""
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", *opts, host, cmd], timeout)


def fresh_env():
    """The environment a brand-new terminal starts with, before ~/.bashrc: not whatever this make run inherited."""
    env = {k: v for k, v in os.environ.items() if k not in ("LAB_SITE", "LOG", "BASH_ENV")}
    env["PATH"] = "/home/vscode/.venvs/lab/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
    return env


def new_terminal(cmd, timeout=20):
    """Run cmd in a fresh interactive bash, the way a new terminal would (it reads ~/.bashrc).
    Returns (exit code, what it printed on stdout): bash -i without a terminal complains on stderr."""
    try:
        p = subprocess.run(["bash", "-ic", cmd], capture_output=True, text=True, timeout=timeout, env=fresh_env(),
                           cwd="/", stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, ""
