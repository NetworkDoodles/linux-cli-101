"""make solve T=1.2 · make break T=4.2 · make live

solve: stuck, or skipped a task? This does the task for you, the same way the guide's solution does, and
fills in that task's answers file. It prints every command it runs, so you can read them.

break: sets up a task's problem on purpose (tasks 4.2, 5.2 and 6.2).

live: task 2.1's minute of new log lines, to watch with tail -f.
"""
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

ROOT, HOME, STATE = lab.ROOT, lab.HOME, lab.STATE
ANSWERS = ROOT / "answers"
BASHRC = HOME / ".bashrc"
WORDS = ["falcon", "harbor", "copper", "meadow", "lantern", "glacier", "orbit", "thistle", "ember", "canyon"]


def say(where, cmd):
    print(f"  {where:<10} {cmd}")


def bash(cmd, where="codespace", cwd=None, check=False):
    """Run a command in the codespace's bash, printing it first."""
    say(where, cmd)
    p = subprocess.run(["bash", "-c", cmd], cwd=cwd or ROOT, capture_output=True, text=True, env=lab.fresh_env())
    if check and p.returncode:
        sys.exit(f"  that failed: {(p.stdout + p.stderr).strip()[:300]}")
    return p.stdout


def on(node, cmd, user="netops"):
    say(node, cmd)
    return lab.sh(node, cmd, user=user, timeout=40)[1]


def fill(task, values):
    """Write values into answers/<task>.yml after their keys, keeping every comment."""
    path = ANSWERS / f"{task}.yml"
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        key = line.split(":")[0].strip()
        if key in values and not line.lstrip().startswith("#"):
            lines[i] = f"{key}: {values[key]}"
    path.write_text("\n".join(lines) + "\n")
    print(f"  {'answers':<10} filled in answers/{task}.yml")


def add_line(path, line):
    text = path.read_text() if path.exists() else ""
    if line not in text.splitlines():
        say("codespace", f"echo '{line}' >> ~/{path.relative_to(HOME)}")
        path.write_text(text + ("" if text.endswith("\n") or not text else "\n") + line + "\n")


def clear_state():
    shutil.rmtree(STATE, ignore_errors=True)
    STATE.mkdir(parents=True, exist_ok=True)


# ── live: task 2.1 ────────────────────────────────────────────────────────────
WRITER = r'''
import sys, time, datetime
path, word = sys.argv[1], sys.argv[2]
for n in range(1, 21):
    now = datetime.datetime.now().strftime("%b %d %H:%M:%S.%f")[:-3]
    msg = f"the word is {word}" if n == 4 else f"keepalive {n} from the live feed"
    with open(path, "a") as f:
        f.write(f"*{now}: %LAB-6-LIVE: {msg}\n")
    time.sleep(3)
'''


def live():
    STATE.mkdir(parents=True, exist_ok=True)
    word = random.choice(WORDS)
    (STATE / "live-word").write_text(word + "\n")
    log = ROOT / "files" / "logs" / "live.log"
    log.write_text("")
    subprocess.Popen([sys.executable, "-c", WRITER, str(log), word], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("\n  files/logs/live.log gets a new line every 3 seconds for the next minute.")
    print("  Watch it:  tail -f files/logs/live.log     (Ctrl+C stops watching)\n")


# ── breaks ────────────────────────────────────────────────────────────────────
def break_4_2():
    w = ROOT / "work"
    (w / "keys").mkdir(parents=True, exist_ok=True)
    (w / "bin").mkdir(parents=True, exist_ok=True)
    key = w / "keys" / "lab_key"
    for p in (key, key.with_suffix(".pub")):
        p.unlink(missing_ok=True)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "lab_key", "-f", str(key)], check=True)
    os.chmod(key, 0o644)
    pub = key.with_suffix(".pub").read_text().strip()
    lab.sh("ws1", f"grep -qF '{pub}' .ssh/authorized_keys 2>/dev/null || "
                  f"(mkdir -p .ssh && chmod 700 .ssh && echo '{pub}' >> .ssh/authorized_keys && chmod 600 .ssh/authorized_keys)",
           user="netops")
    (w / "bin" / "hello.sh").write_text('#!/usr/bin/env bash\necho "hello from work/bin"\n')
    os.chmod(w / "bin" / "hello.sh", 0o644)
    (w / "team-notes.txt").write_text("Team notes: anyone may read these. Only you should change them.\n")
    os.chmod(w / "team-notes.txt", 0o666)
    print("\n  Three things in work/ have the wrong permissions now:")
    print("    work/keys/lab_key      a private key that ws1 accepts:  ssh -i work/keys/lab_key netops@ws1")
    print("    work/bin/hello.sh      a script that won't run:          work/bin/hello.sh")
    print("    work/team-notes.txt    a file anyone can change\n")


HOG = """#!/usr/bin/env bash
# labhog: a runaway, for task 5.2. It ignores the polite signals and stops by itself after 30 minutes.
trap '' TERM INT HUP
end=$((SECONDS + 1800))
while [ "$SECONDS" -lt "$end" ]; do :; done
"""


def break_5_2():
    STATE.mkdir(parents=True, exist_ok=True)
    hog = pathlib.Path("/tmp/labhog")
    hog.write_text(HOG)
    os.chmod(hog, 0o755)
    p = subprocess.Popen([str(hog)], start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (STATE / "hog.pid").write_text(f"{p.pid}\n")
    print("\n  Something in the codespace is eating a whole CPU now. Find it, then stop it.\n")


def break_6_2():
    lab.sh("srv1", "rm -f /etc/ssh/ssh_host_* && ssh-keygen -q -A && pkill -HUP -x sshd")
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "6.2-broken").write_text("srv1's host keys were made again\n")
    print("\n  srv1 has been rebuilt: same name, same address, new host keys. Try: ssh srv1\n")


# ── solutions ─────────────────────────────────────────────────────────────────
def solve_1_1():
    bash("pwd")
    bash("echo ~")
    bash("cat /etc/os-release")
    bash("ls -a files")
    os_name = next(l.split("=", 1)[1].strip('"') for l in pathlib.Path("/etc/os-release").read_text().splitlines()
                   if l.startswith("PRETTY_NAME="))
    fill("1.1", {"home": HOME, "repo": ROOT, "os": os_name, "hidden_file": ".lab-notes",
                 "ls_sizes_option": "-h", "logs_folder": "/var/log"})


def solve_1_2():
    bash("ls -R files/site")
    fill("1.2", {"chi_leaf2_absolute": ROOT / "files/site/chi/rack2/chi-leaf2.cfg",
                 "from_nyc_rack1": "../../chi/rack2/chi-leaf2.cfg", "readme_from_chi_rack2": "../README.txt",
                 "parent_of_home": HOME.parent})


def solve_2_1():
    lines = (ROOT / "files/logs/r1.log").read_text().splitlines()
    bash("head -n 1 files/logs/r1.log")
    bash("tail -n 1 files/logs/r1.log")
    bash("grep -m 1 'LINK_DOWN: Interface GigabitEthernet1 ' files/logs/r1.log")
    first_down = next(l.split()[2][:8] for l in lines if "LINK_DOWN: Interface GigabitEthernet1 " in l)
    ev = lambda l: re.search(r"%[A-Z]+-\d-([A-Z_]+):", l).group(1)  # noqa: E731
    if not (STATE / "live-word").exists() or "the word is" not in (ROOT / "files/logs/live.log").read_text(errors="ignore"):
        say("codespace", "make live      (then wait for the word)")
        live()
        for _ in range(30):
            if "the word is" in (ROOT / "files/logs/live.log").read_text():
                break
            time.sleep(1)
    word = (STATE / "live-word").read_text().strip()
    add_line(HOME / "notes.txt", "checked r1")
    fill("2.1", {"first_event": ev(lines[0]), "last_event": ev(lines[-1]), "gi1_down_time": first_down,
                 "live_word": word})


def solve_2_2():
    empty = bash("find files -name '*.cfg' -empty").split()
    leaf2 = bash("find files -name '*leaf2*'").splitlines()
    b = "cd files/backups && "
    bash(b + "mkdir -p r1 sw1")
    bash(b + "mv 'sw1 2026-11-02.cfg' sw1-2026-11-02.cfg")
    bash(b + "find . -maxdepth 1 -name '*.cfg' -empty -delete")
    bash(b + "mv r1-*.cfg r1/")
    bash(b + "mv sw1-*.cfg sw1/")
    fill("2.2", {"empty_files": len(empty) or 2, "leaf2_files": len(leaf2) or 4})


PIPES_3_1 = {
    "gi2_lines": 'grep -c GigabitEthernet2 "$LOG"',
    "failed_lines": 'grep LOGIN_FAILED "$LOG"',
    "not_config": 'grep -vc CONFIG_DONE "$LOG"',
    "downs_per_interface": "grep LINK_DOWN \"$LOG\" | cut -d' ' -f6 | sort | uniq -c | sort -rn",
    "save_errors": "grep -- -3- \"$LOG\" > reports/errors.txt",
}
PIPES_3_2 = {
    "failed_total": 'grep -c LOGIN_FAILED "$LOG"',
    "failed_by_user": "grep LOGIN_FAILED \"$LOG\" | cut -d' ' -f8 | sort | uniq -c | sort -rn",
    "users_once": "grep LOGIN_FAILED \"$LOG\" | cut -d' ' -f8 | sort -u",
}


def solve_3_1():
    fill("3.1", PIPES_3_1)


def solve_3_2():
    fill("3.2", PIPES_3_2)


def solve_4_1():
    bash("ls -l /etc/shadow")
    bash("mkdir -p work && touch work/private.txt && chmod 600 work/private.txt")
    bash("printf '#!/usr/bin/env bash\\necho \"it runs\"\\n' > work/run.sh && chmod 755 work/run.sh")
    if not shutil.which("traceroute", path="/usr/sbin:/usr/bin:/sbin:/bin"):
        bash("sudo apt-get update -qq && sudo apt-get install -y -qq traceroute", check=True)
    import grp
    import pwd
    st = os.stat("/etc/shadow")
    fill("4.1", {"shadow_owner": pwd.getpwuid(st.st_uid).pw_name, "shadow_group": grp.getgrgid(st.st_gid).gr_name,
                 "without_sudo": "Permission denied"})


def solve_4_2():
    if not (ROOT / "work/keys/lab_key").exists():
        break_4_2()
    bash("chmod 600 work/keys/lab_key")
    bash("chmod 755 work/bin/hello.sh")
    bash("chmod 644 work/team-notes.txt")
    fill("4.2", {"ssh_warning": "UNPROTECTED"})


def solve_5_1():
    add_line(BASHRC, "export LAB_SITE=nyc")
    code, py = lab.new_terminal("command -v python")
    fill("5.1", {"shell_name": "bash", "python_path": py.splitlines()[-1] if py else "", "stopped_word": "Stopped",
                 "top_quit_key": "q"})


def solve_5_2():
    pidfile = STATE / "hog.pid"
    if not pidfile.exists():
        break_5_2()
        time.sleep(1)
    pid = pidfile.read_text().strip()
    bash("ps -eo pid,pcpu,comm --sort=-pcpu | head -n 5")
    bash(f"kill {pid}; sleep 1; ps -p {pid} -o pid,comm || true")
    bash(f"kill -9 {pid}; sleep 1; ps -p {pid} -o pid,comm || true")
    bash("mkdir -p ~/tools && cp files/labinfo ~/tools/ && chmod +x ~/tools/labinfo")
    add_line(BASHRC, 'export PATH="$HOME/tools:$PATH"')
    fill("5.2", {"hog_pid": pid, "signal_that_worked": "KILL"})


def ws1_key_ready():
    key = HOME / ".ssh" / "id_ed25519"
    if not key.exists():
        bash('mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519')
    return key.with_suffix(".pub").read_text().strip()


def authorize(node, pub):
    say(node, "the key into ~netops/.ssh/authorized_keys (what ssh-copy-id does)")
    lab.sh(node, f"grep -qF '{pub}' .ssh/authorized_keys 2>/dev/null || "
                 f"(mkdir -p .ssh && chmod 700 .ssh && echo '{pub}' >> .ssh/authorized_keys && chmod 600 .ssh/authorized_keys)",
           user="netops")


def trust(host):
    if lab.run(["ssh-keygen", "-F", host], 10)[0] != 0:
        bash(f"ssh-keyscan -H -t ed25519 {host} >> ~/.ssh/known_hosts 2>/dev/null")


def solve_6_1():
    pub = ws1_key_ready()
    trust("ws1")
    authorize("ws1", pub)
    code, out = lab.sh("ws1", "ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub")
    bash("ssh -o BatchMode=yes netops@ws1 hostname")
    fill("6.1", {"ws1_fingerprint": out.split()[1]})


SSH_CONFIG = """# The lab's machines (task 6.2)
Host ws1
    User netops
Host srv1
    User netops
Host r1
    User admin
"""


def solve_6_2():
    pub = ws1_key_ready()
    cfg = HOME / ".ssh" / "config"
    text = cfg.read_text() if cfg.exists() else ""
    if "# The lab's machines (task 6.2)" not in text:
        say("codespace", "the Host blocks for ws1, srv1 and r1 into ~/.ssh/config")
        cfg.write_text(text + ("\n" if text and not text.endswith("\n") else "") + SSH_CONFIG)
        os.chmod(cfg, 0o600)
    trust("ws1")
    authorize("ws1", pub)
    authorize("srv1", pub)
    if not (STATE / "6.2-broken").exists():
        say("make", "break T=6.2")
        break_6_2()
    bash("ssh-keygen -R srv1 >/dev/null 2>&1; true")
    bash("ssh-keyscan -H -t ed25519 srv1 >> ~/.ssh/known_hosts 2>/dev/null")
    bash("scp -q files/notes/handover.txt srv1:", check=True)
    bash("ssh srv1 ls -l handover.txt")


REACH = '''#!/usr/bin/env bash
# reach.sh: ping every host in a list, say which ones answer, and fail if any of them doesn't.
#
#   scripts/reach.sh [FILE]     FILE has one host per line; without one, it reads hosts.txt
#
# It prints one line per host, "ws1 up" or "ws1 down", and exits 0 if every host answered, 1 if not.
# Task 7.1: https://networkdoodles.com/labs/linux-cli-101/task-7-1/

file="${1:-hosts.txt}"        # the first argument, or hosts.txt if there isn't one
down=0                        # becomes 1 as soon as one host doesn't answer

while read -r host; do
  case "$host" in ""|"#"*) continue ;; esac      # skip blank lines and comments

  if ping -c 1 -W 1 "$host" >/dev/null 2>&1; then
    echo "$host up"
  else
    echo "$host down"
    down=1
  fi

done < "$file"

exit "$down"
'''

AUDIT = '''#!/usr/bin/env bash
# audit.sh: list the configs in a folder that have no "ntp server" line.
#
#   scripts/audit.sh DIR
#
# For every .cfg file in DIR (names can have spaces in them), print its name if no line in it starts with
# "ntp server". Other files are left alone. Exit 1 if it printed any, 0 if every config was fine (an empty
# folder is fine). With no DIR, or a DIR that isn't a folder, print a usage line on stderr and exit 2.
# Task 7.2: https://networkdoodles.com/labs/linux-cli-101/task-7-2/

dir="${1:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then
  echo "usage: $0 DIR   (DIR is a folder of .cfg files)" >&2
  exit 2
fi

missing=0
for f in "$dir"/*.cfg; do
  [ -e "$f" ] || continue                  # an empty folder: the pattern matched nothing
  if ! grep -q '^ntp server' "$f"; then
    basename "$f"
    missing=1
  fi
done

exit "$missing"
'''


def solve_7_1():
    say("editor", "scripts/reach.sh: the ping, the two echo lines and exit \"$down\"")
    (ROOT / "scripts/reach.sh").write_text(REACH)
    bash("chmod +x scripts/reach.sh")
    print(bash("./scripts/reach.sh; echo \"exit code $?\"").rstrip())


def solve_7_2():
    say("editor", "scripts/audit.sh: the usage check, the loop and the exit code")
    (ROOT / "scripts/audit.sh").write_text(AUDIT)
    bash("chmod +x scripts/audit.sh")
    print(bash("./scripts/audit.sh files/configs; echo \"exit code $?\"").rstrip())


def solve_8_1():
    on("ws1", "ip -br addr")
    on("ws1", "ip route")
    on("ws1", "dig +short srv1.lab")
    on("ws1", "cat /etc/resolv.conf")
    out = on("ws1", "traceroute -n -q 1 -w 1 -m 5 192.168.20.10")
    hops = len([l for l in out.splitlines()[1:] if l.strip()])
    out = on("ws1", "ip route get 192.168.20.10")
    dev = out.split()[out.split().index("dev") + 1]
    fill("8.1", {"gateway": "192.168.10.1", "mgmt_interface": "eth0", "srv1_address": "192.168.20.10",
                 "dns_server": "192.168.20.10", "hops_to_srv1": hops, "route_dev": dev})


def solve_8_2():
    on("ws1", "curl -sv -m 3 http://srv1:8080/ 2>&1 | grep -i 'refused\\|failed' | head -n 2")
    on("srv1", "ss -tlnp")
    on("srv1", "sudo sed -i 's/^BIND=.*/BIND=0.0.0.0/' /etc/labweb.conf")
    on("srv1", "sudo labweb restart")
    on("ws1", "curl -s http://srv1:8080/")
    fill("8.2", {"curl_said": "refused", "listen_before": "127.0.0.1", "listen_after": "0.0.0.0"})


def solve_8_3():
    code, conf = lab.sh("srv1", "cat /etc/labweb.conf")
    if "BIND=127.0.0.1" in conf:
        print("  (task 8.2 isn't done yet, so doing it first)")
        solve_8_2()
    on("ws1", "rm -f web.pcap; (sudo timeout 8 tcpdump -n -i eth1 -w web.pcap port 8080 >/dev/null 2>&1 &); sleep 2; "
              "curl -s http://srv1:8080/ >/dev/null; sleep 1; sudo pkill -INT -x tcpdump; sleep 1; "
              "sudo chown netops: web.pcap")
    bash("mkdir -p captures && scp -q ws1:web.pcap captures/", check=True)
    out = bash("tcpdump -n -r captures/web.pcap 2>/dev/null")
    pkts = [l for l in out.splitlines() if re.match(r"\d\d:\d\d:\d\d", l)]
    syn = next(l for l in pkts if "Flags [S]," in l)
    fill("8.3", {"client_port": syn.split()[2].rsplit(".", 1)[1], "packets": len(pkts)})


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "clear-state":
        clear_state()
        sys.exit(0)
    if action == "live":
        live()
        sys.exit(0)
    task = sys.argv[2] if len(sys.argv) > 2 else ""
    fn = globals().get(f"{action}_{task.replace('.', '_')}")
    if not fn:
        sys.exit(f"no {action} for task {task}" + ("   (tasks 4.2, 5.2 and 6.2 have one)" if action == "break" else ""))
    print(f"\n  {action} task {task}:\n")
    fn()
    if action == "solve":
        print(f"\n  done. Now: make check T={task}\n")
