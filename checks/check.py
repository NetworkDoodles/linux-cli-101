"""make check T=1.1 · CH=1 · (nothing)  ·  verifies a task, a chapter or the whole lab.

Every check reads the real thing: your answers are compared with what the codespace, ws1, srv1 and r1 say
right now. Pipelines and scripts you write are run again on files they haven't seen, so a command that only
works on the example won't pass.

    python checks/check.py 1.1          one task
    python checks/check.py ch1          one chapter
    python checks/check.py all          everything
"""
import hashlib
import os
import pathlib
import random
import re
import shutil
import stat
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "lab").as_posix())
import lab  # noqa: E402

GUIDE = "https://networkdoodles.com/labs/linux-cli-101"
TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
C = {k: (v if TTY else "") for k, v in dict(g="\033[32m", r="\033[31m", y="\033[33m", c="\033[36m", d="\033[2m",
                                              b="\033[1m", x="\033[0m").items()}
HOME = lab.HOME


# ── reading your answers ───────────────────────────────────────────────────────
def answers(task):
    """answers/<task>.yml as a dict of strings, read line by line: `key: value`. The value is everything after
    the first colon, exactly as typed (so a pipeline's quotes and colons stay as they are)."""
    p = ROOT / "answers" / f"{task}.yml"
    doc = {}
    for line in (p.read_text().splitlines() if p.exists() else []):
        if line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if re.fullmatch(r"[a-z0-9_]+", key.strip()):
            doc[key.strip()] = value.strip()
    return doc


def blank(v):
    return v is None or str(v).strip() == ""


def plain(v):
    """An answer that's a word, a number or a path: no comment, no surrounding quotes."""
    v = str(v or "").strip()
    if v.startswith("#"):
        return ""
    return re.split(r"\s+#", v)[0].strip().strip("'\"").strip()


def ask(doc, key, want, label, norm=lambda s: s, hint="but that's not what the system says. Look again."):
    given = plain(doc.get(key))
    if not given:
        return False, f"{label}: {key} is still blank in the answers file"
    wants = want if isinstance(want, (set, list, tuple)) else {want}
    if norm(given) in {norm(str(w)) for w in wants if w is not None}:
        return True, f"{label}: {given}"
    return False, f"{label}: you wrote {given}, {hint}"


def low(s):
    return str(s).strip().lower()


def need(*nodes):
    down = [n for n in nodes if not lab.ready(n)]
    if down:
        raise RuntimeError(f"{', '.join(down)} isn't running: is the lab up? (make status, make up)")


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def octal(path):
    return f"{mode(path):03o}" if os.path.exists(path) else "missing"


# ── pipelines and scripts, run on files they haven't seen ─────────────────────
def pipeline(cmd, log, cwd=None):
    """Run one of your pipelines with LOG pointing at a log file, the way you ran it in the terminal."""
    env = lab.fresh_env()
    env["LOG"] = str(log)
    return lab.run(["bash", "-c", cmd], 20, env=env, cwd=cwd or ROOT)


def counts(text):
    """`uniq -c` output (`   3 netops`) as [(3, 'netops'), ...]; None if a line isn't count-then-word."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r"\s*(\d+)\s+(\S+)\s*", line)
        if not m:
            return None
        rows.append((int(m.group(1)), m.group(2)))
    return rows


def most_first(given, want):
    """Same counts for the same names, biggest first (names with equal counts may come in any order)."""
    rows = counts(given)
    if rows is None:
        return False, "each line should be a count, then a name, the way uniq -c prints it"
    if sorted(rows) != sorted((n, k) for k, n in want.items()):
        return False, f"the counts aren't right (got {', '.join(f'{k} {n}' for n, k in rows[:4]) or 'nothing'})"
    if [n for n, _ in rows] != sorted((n for n, _ in rows), reverse=True):
        return False, "the counts are right, but not biggest first"
    return True, ""


USERS = ["guest", "netops", "support", "operator", "backup", "test", "pi", "ubnt", "admin1", "monitor"]


def fake_log(seed):
    """A log in r1's own format, with a different mix of events each time."""
    rnd = random.Random(seed)
    day, t = rnd.randint(12, 28), rnd.randint(3600, 70000)
    lines, facts = [], {"down": {}, "failed": {}, "gi2": 0}

    def at():
        nonlocal t
        t += rnd.randint(1, 40)
        h, m, s = t // 3600, t // 60 % 60, t % 60
        return f"*Nov {day} {h:02d}:{m:02d}:{s:02d}.{rnd.randint(0, 999):03d}:"

    lines.append(f"{at()} %CAPEOS-5-RESTART: CapeOS 0.11.0 started")
    for _ in range(rnd.randint(8, 16)):
        kind = rnd.random()
        if kind < 0.4:
            i = f"GigabitEthernet{rnd.randint(1, 4)}"
            stamp = at()
            lines += [f"{stamp} %CAPEOS-3-LINK_DOWN: Interface {i} is down (administratively)",
                      f"{stamp} %CAPEOS-5-PROTO_DOWN: Line protocol on {i} is down",
                      f"{stamp} %CAPEOS-5-CONFIG_DONE: Configured from console by root",
                      f"{at()} %CAPEOS-5-CONFIG_DONE: Configured from console by root"]
            stamp = at()
            lines += [f"{stamp} %CAPEOS-3-LINK_UP: Interface {i} is up",
                      f"{stamp} %CAPEOS-5-PROTO_UP: Line protocol on {i} is up"]
            facts["down"][i] = facts["down"].get(i, 0) + 1
        elif kind < 0.8:
            u = rnd.choice(USERS[: rnd.randint(3, len(USERS))])
            lines.append(f"{at()} %CAPEOS-4-LOGIN_FAILED: Login failed for {u} from 172.80.102.1 port "
                         f"{rnd.randint(32768, 60999)}")
            facts["failed"][u] = facts["failed"].get(u, 0) + 1
        else:
            lines.append(f"{at()} %CAPEOS-5-LOGIN_OK: Login by admin from 172.80.102.1 port {rnd.randint(32768, 60999)}")
    facts["gi2"] = sum("GigabitEthernet2" in ln for ln in lines)
    return "\n".join(lines) + "\n", facts


def logs_to_try():
    """The real practice log first, then three it hasn't seen."""
    out = [ROOT / "files" / "logs" / "r1.log"]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lcli-logs-"))
    for seed in (101, 202, 303):
        text, _ = fake_log(seed)
        (tmp / f"router-{seed}.log").write_text(text)
        out.append(tmp / f"router-{seed}.log")
    return out


def log_facts(path):
    lines = path.read_text().splitlines()
    down, failed = {}, {}
    for ln in lines:
        m = re.search(r"LINK_DOWN: Interface (\S+)", ln)
        if m:
            down[m.group(1)] = down.get(m.group(1), 0) + 1
        m = re.search(r"LOGIN_FAILED: Login failed for (\S+)", ln)
        if m:
            failed[m.group(1)] = failed.get(m.group(1), 0) + 1
    return lines, down, failed


def on_every_log(doc, key, label, judge):
    """Run your pipeline on every log; judge(output, path) returns (ok, why)."""
    cmd = doc.get(key, "")
    if blank(cmd):
        return False, f"{label}: {key} is still blank in the answers file"
    for path in logs_to_try():
        code, out = pipeline(cmd, path)
        ok, why = judge(out, path)
        if not ok:
            which = "files/logs/r1.log" if path.name == "r1.log" else f"a log it hadn't seen ({path.name})"
            return False, f"{label}: on {which}, {why}"
    return True, f"{label}: right on r1.log and on three logs it hadn't seen"


# ── chapter 1 · the shell and the filesystem ──────────────────────────────────
def os_name():
    for line in pathlib.Path("/etc/os-release").read_text().splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return None


def t1_1():
    doc = answers("1.1")
    yield ask(doc, "home", str(HOME), "your home folder (follow along)", lambda s: s.rstrip("/"))
    yield ask(doc, "repo", str(ROOT), "the lab's folder (follow along)", lambda s: s.rstrip("/"),
              "but that's not where the terminal opens. What does pwd print in a new terminal?")
    yield ask(doc, "os", os_name(), "the operating system (follow along)", low,
              "but that's not what /etc/os-release says on its PRETTY_NAME line.")
    yield ask(doc, "hidden_file", ".lab-notes", "the hidden file in files/ (follow along)", low,
              "but that's not it. ls -a files shows the names that start with a dot.")
    yield ask(doc, "ls_sizes_option", {"-h", "--human-readable"}, "the ls option for sizes in K and M (challenge)",
              lambda s: low(s) if low(s).startswith("-") else "-" + low(s), "but that's not the one ls --help lists for that.")
    yield ask(doc, "logs_folder", "/var/log", "where Linux keeps its logs (challenge)", lambda s: s.rstrip("/"))


def resolves(given, start, want):
    if given.startswith("/") or given.startswith("~"):
        return False
    return os.path.normpath(os.path.join(start, given)) == os.path.normpath(want)


def t1_2():
    doc = answers("1.2")
    site = ROOT / "files" / "site"
    target = site / "chi" / "rack2" / "chi-leaf2.cfg"
    given = plain(doc.get("chi_leaf2_absolute"))
    ok = given.startswith("/") and os.path.normpath(given) == str(target)
    yield (ok, f"the absolute path to chi-leaf2.cfg (challenge): {given or 'still blank'}"
               + ("" if ok or not given else ". It should start at / and lead to the file."))
    for key, start, want, what in (
            ("from_nyc_rack1", site / "nyc" / "rack1", target, "chi-leaf2.cfg from files/site/nyc/rack1"),
            ("readme_from_chi_rack2", site / "chi" / "rack2", site / "chi" / "README.txt",
             "chi's README.txt from files/site/chi/rack2")):
        given = plain(doc.get(key))
        ok = bool(given) and resolves(given, start, want)
        yield (ok, f"a relative path to {what} (challenge): {given or 'still blank'}"
                   + ("" if ok or not given else ". Start from that folder; each .. is one folder up."))
    yield ask(doc, "parent_of_home", str(HOME.parent), "the folder your home folder is in (challenge)",
              lambda s: s.rstrip("/") or "/")


# ── chapter 2 · working with files ────────────────────────────────────────────
def event(line):
    m = re.search(r"%[A-Z]+-\d-([A-Z_]+):", line)
    return m.group(1) if m else None


def t2_1():
    doc = answers("2.1")
    lines = (ROOT / "files" / "logs" / "r1.log").read_text().splitlines()
    ev = lambda s: low(s).lstrip("%").split("-")[-1].rstrip(":")  # noqa: E731
    yield ask(doc, "first_event", event(lines[0]), "the first line's event (follow along)", ev)
    yield ask(doc, "last_event", event(lines[-1]), "the last line's event (follow along)", ev)
    first_down = next((ln.split()[2].rstrip(":") for ln in lines if "LINK_DOWN" in ln and "GigabitEthernet1 " in ln), "")
    yield ask(doc, "gi1_down_time", first_down[:8], "when GigabitEthernet1 first went down (follow along)",
              lambda s: s[:8], "but that's not the first LINK_DOWN for GigabitEthernet1. Search for it in less with /.")
    word = (lab.STATE / "live-word").read_text().strip() if (lab.STATE / "live-word").exists() else None
    if word is None:
        yield False, "the word from live.log (follow along): run make live first, then tail -f files/logs/live.log"
    else:
        yield ask(doc, "live_word", word, "the word that appeared in live.log (follow along)", low,
                  "but that's not the word in the newest live.log. Did you run make live again?")
    notes = HOME / "notes.txt"
    text = notes.read_text() if notes.exists() else ""
    yield ("checked r1" in text.lower(),
           "~/notes.txt, written in nano, says checked r1 (challenge)"
           + ("" if "checked r1" in text.lower() else (": the file isn't there" if not notes.exists() else ": it doesn't say checked r1 yet")))


BACKUPS = {   # what files/backups should hold when it's tidy: path → sha256 of the file it started as
    "README.txt": None,
    "r1/r1-2026-11-01.cfg": "r1-2026-11-01.cfg",
    "r1/r1-2026-11-02.cfg": "r1-2026-11-02.cfg",
    "sw1/sw1-2026-11-01.cfg": "sw1-2026-11-01.cfg",
    "sw1/sw1-2026-11-02.cfg": "sw1 2026-11-02.cfg",
}


def git_blob(path):
    code, out = lab.run(["git", "-C", str(ROOT), "show", f"main~0:{path}"], 10)
    if code:
        code, out = lab.run(["git", "-C", str(ROOT), "log", "--all", "--format=%H", "--diff-filter=A", "--", path], 10)
        first = out.split()[-1] if out.split() else ""
        code, out = lab.run(["git", "-C", str(ROOT), "show", f"{first}:{path}"], 10)
    return hashlib.sha256((out + "\n").encode()).hexdigest() if code == 0 else None


def t2_2():
    doc = answers("2.2")
    yield ask(doc, "empty_files", 2, "how many empty .cfg files find found (challenge)", low,
              "but that's not what find files -name '*.cfg' -empty counts. Count them before you delete them.")
    yield ask(doc, "leaf2_files", 4, "how many files under files/ have leaf2 in their name (challenge)", low,
              "but find counts a different number. Remember the name with a space in it.")
    b = ROOT / "files" / "backups"
    have = sorted(str(p.relative_to(b)) for p in b.rglob("*") if p.is_file())
    want = sorted(BACKUPS)
    yield (have == want, "files/backups holds r1/ and sw1/, two configs each, and the README (challenge)"
           + ("" if have == want else f": it holds {', '.join(have) or 'nothing'}"))
    if have == want:
        same = all(hashlib.sha256((b / k).read_bytes()).hexdigest() == git_blob(f"files/backups/{v}")
                   for k, v in BACKUPS.items() if v)
        yield (same, "each config is the one it started as, just moved or renamed (challenge)"
               + ("" if same else ": one of them has different content. git diff shows what changed"))


# ── chapter 3 · pipelines ─────────────────────────────────────────────────────
def t3_1():
    doc = answers("3.1")
    yield on_every_log(doc, "gi2_lines", "how many lines mention GigabitEthernet2 (follow along)",
                       lambda out, p: (out.strip() == str(sum("GigabitEthernet2" in ln for ln in p.read_text().splitlines())),
                                       f"it printed {out.strip()[:40] or 'nothing'}"))
    yield on_every_log(doc, "failed_lines", "only the LOGIN_FAILED lines (follow along)",
                       lambda out, p: (out.splitlines() == [ln for ln in p.read_text().splitlines() if "LOGIN_FAILED" in ln],
                                       "it printed other lines too, or missed some"))
    yield on_every_log(doc, "not_config", "how many lines are not CONFIG_DONE (follow along)",
                       lambda out, p: (out.strip() == str(sum("CONFIG_DONE" not in ln for ln in p.read_text().splitlines())),
                                       f"it printed {out.strip()[:40] or 'nothing'}"))
    yield on_every_log(doc, "downs_per_interface", "LINK_DOWN events per interface, most first (challenge)",
                       lambda out, p: most_first(out, log_facts(p)[1]))
    cmd = doc.get("save_errors", "")
    if blank(cmd):
        yield False, "every severity 3 line into reports/errors.txt (challenge): save_errors is still blank"
        return
    for path in logs_to_try():
        dest = ROOT / "reports" / "errors.txt"
        dest.unlink(missing_ok=True)
        code, out = pipeline(cmd, path)
        want = [ln for ln in path.read_text().splitlines() if re.search(r"%[A-Z]+-3-", ln)]
        got = dest.read_text().splitlines() if dest.exists() else None
        if got != want:
            yield (False, "every severity 3 line into reports/errors.txt (challenge): "
                   + ("reports/errors.txt wasn't written: use > to send the output there" if got is None else
                      f"on {path.name}, the file has {len(got)} lines, not the {len(want)} with -3-"))
            return
        if out.strip():
            yield False, "every severity 3 line into reports/errors.txt (challenge): it printed lines too; they should only go to the file"
            return
    yield True, "every severity 3 line into reports/errors.txt (challenge): right on r1.log and on three logs it hadn't seen"


def t3_2():
    doc = answers("3.2")
    yield on_every_log(doc, "failed_total", "how many failed logins (challenge)",
                       lambda out, p: (out.strip() == str(sum(log_facts(p)[2].values())), f"it printed {out.strip()[:40] or 'nothing'}"))
    yield on_every_log(doc, "failed_by_user", "failed logins per user, most first (challenge)",
                       lambda out, p: most_first(out, log_facts(p)[2]))
    yield on_every_log(doc, "users_once", "every user who failed, once each, A to Z (challenge)",
                       lambda out, p: (out.split() == sorted(log_facts(p)[2]) and len(out.splitlines()) == len(log_facts(p)[2]),
                                       f"it printed {', '.join(out.split()[:5]) or 'nothing'}"))


# ── chapter 4 · users and permissions ─────────────────────────────────────────
def t4_1():
    doc = answers("4.1")
    shadow = os.stat("/etc/shadow")
    import grp
    import pwd
    yield ask(doc, "shadow_owner", pwd.getpwuid(shadow.st_uid).pw_name, "who owns /etc/shadow (follow along)", low)
    yield ask(doc, "shadow_group", grp.getgrgid(shadow.st_gid).gr_name, "its group (follow along)", low)
    yield ask(doc, "without_sudo", "permission denied", "what cat /etc/shadow says without sudo (follow along)",
              lambda s: low(s).split(":")[-1].strip(), "but cat said something else. Look at the end of its message.")
    w = ROOT / "work"
    for name, want, what in (("private.txt", 0o600, "only you can read and write it"),
                             ("run.sh", 0o755, "everyone can run it, only you can change it")):
        p = w / name
        ok = p.exists() and mode(p) == want
        yield ok, f"work/{name} is {want:o}: {what} (follow along){'' if ok else f': it is {octal(p)}'}"
    ok = shutil.which("traceroute", path="/usr/sbin:/usr/bin:/sbin:/bin") is not None
    yield ok, "traceroute is installed in the codespace (challenge)" + ("" if ok else ": sudo apt update, then sudo apt install traceroute")


def t4_2():
    need("ws1")
    doc = answers("4.2")
    w = ROOT / "work"
    key, hello, notes = w / "keys" / "lab_key", w / "bin" / "hello.sh", w / "team-notes.txt"
    if not key.exists():
        yield False, "make break T=4.2 sets this task up: run it first"
        return
    yield ask(doc, "ssh_warning", "unprotected", "the word ssh shouted about the key (challenge)",
              lambda s: "unprotected" if "unprotected" in low(s) else low(s))
    m = mode(key)
    yield (m & 0o077 == 0, f"work/keys/lab_key: only you can read it (challenge): it is {m:03o}")
    code, out = lab.run(["ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
                         "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                         "netops@ws1", "hostname"], 15)
    yield (code == 0 and out.strip() == "ws1", "and ssh logs in to ws1 with it (challenge)" + ("" if code == 0 else f": {out.splitlines()[-1][:120] if out else 'no answer'}"))
    m = mode(hello)
    code, out = lab.run([str(hello)], 10)
    yield (code == 0 and m & 0o100 and not m & 0o022,
           f"work/bin/hello.sh runs, and only you can change it (challenge): it is {m:03o}"
           + ("" if code == 0 else ", and running it says permission denied"))
    m = mode(notes)
    yield (not m & 0o002 and m & 0o044 == 0o044, f"work/team-notes.txt: everyone can read it, not everyone can change it (challenge): it is {m:03o}")


# ── chapter 5 · processes, environment variables and PATH ─────────────────────
def t5_1():
    doc = answers("5.1")
    yield ask(doc, "shell_name", "bash", "the shell you're typing into (follow along)", lambda s: low(s).split("/")[-1])
    code, out = lab.new_terminal("command -v python")
    yield ask(doc, "python_path", out.strip() if code == 0 else None, "which python a new terminal runs (follow along)",
              lambda s: s.rstrip("/"), "but that's not what which python prints.")
    yield ask(doc, "stopped_word", "stopped", "what jobs says after Ctrl+Z (follow along)", lambda s: low(s).split()[-1] if s.split() else s)
    yield ask(doc, "top_quit_key", "q", "the key that quits top (follow along)", low)
    code, out = lab.new_terminal('echo "$LAB_SITE"')
    yield (out.strip().endswith("nyc"), f"a new terminal has LAB_SITE=nyc, from ~/.bashrc (challenge): {out.strip().splitlines()[-1] if out.strip() else 'not set'}")
    code, out = lab.new_terminal("bash -c 'echo \"$LAB_SITE\"'")
    child = out.strip().splitlines()[-1] if out.strip() else ""
    yield (child == "nyc", "and the programs it starts see it too: it's exported (challenge)"
           + ("" if child == "nyc" else ": a child process doesn't see it. Did you export it?"))


def t5_2():
    doc = answers("5.2")
    pidfile = lab.STATE / "hog.pid"
    if not pidfile.exists():
        yield False, "make break T=5.2 sets this task up: run it first"
        return
    pid = pidfile.read_text().strip()
    yield ask(doc, "hog_pid", pid, "the runaway's process ID (challenge)", low, "but that's not labhog's PID. ps or top shows it.")
    alive = os.path.exists(f"/proc/{pid}")
    yield (not alive, "labhog is stopped (challenge)" + ("" if not alive else ": it's still running"))
    yield ask(doc, "signal_that_worked", "kill", "the signal that stopped it (challenge)",
              lambda s: low(s).removeprefix("sig").replace("-", "").replace("9", "kill"),
              "but labhog ignores that one. Which signal can't a process ignore?")
    code, where = lab.new_terminal("command -v labinfo")
    where = where.strip().splitlines()[-1] if where.strip() else ""
    want = str(HOME / "tools" / "labinfo")
    yield (where == want, f"a new terminal finds labinfo in ~/tools, from any folder (challenge): {where or 'command not found'}")
    code, out = lab.new_terminal("labinfo")
    yield (code == 0 and "labinfo:" in out, "and labinfo runs (challenge)" + ("" if code == 0 else ": " + (out.splitlines()[-1][:100] if out else "no output")))


# ── chapter 6 · SSH and keys ──────────────────────────────────────────────────
def fingerprints(node):
    code, out = lab.sh(node, "for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf $f; done")
    return {w for w in out.split() if w.startswith("SHA256:")}


def known(host):
    return lab.run(["ssh-keygen", "-F", host], 10)[0] == 0


def t6_1():
    need("ws1")
    doc = answers("6.1")
    yield ask(doc, "ws1_fingerprint", fingerprints("ws1"), "ws1's host key fingerprint (follow along)",
              lambda s: s.strip().rstrip("."), "but that's not one of ws1's host keys. Copy it from the question ssh asked.")
    yield known("ws1"), "ws1 is in your known_hosts (follow along)"
    key = HOME / ".ssh" / "id_ed25519"
    ok = key.exists() and (HOME / ".ssh" / "id_ed25519.pub").exists()
    yield ok, "you have an ed25519 key pair in ~/.ssh (follow along)" + ("" if ok else ": ssh-keygen -t ed25519 makes one")
    if not ok:
        return
    pub = (HOME / ".ssh" / "id_ed25519.pub").read_text().split()[1]
    code, out = lab.sh("ws1", "cat /home/netops/.ssh/authorized_keys 2>/dev/null")
    yield pub in out, "your public key is in netops's authorized_keys on ws1 (follow along)"
    code, out = lab.ssh("netops@ws1", "hostname")
    yield (code == 0 and out.strip() == "ws1", "ssh netops@ws1 logs in without a password (follow along)"
           + ("" if code == 0 else f": {out.splitlines()[-1][:120] if out else 'no answer'}"))


def ssh_g(host):
    code, out = lab.run(["ssh", "-G", host], 10)
    return dict(line.split(" ", 1) for line in out.splitlines() if " " in line)


def t6_2():
    need("ws1", "srv1", "r1")
    for host, user in (("ws1", "netops"), ("srv1", "netops"), ("r1", "admin")):
        g = ssh_g(host)
        yield g.get("user") == user, f"~/.ssh/config: ssh {host} logs in as {user} (challenge): it would use {g.get('user')}"
    code, out = lab.ssh("ws1", "hostname")
    yield code == 0 and out.strip() == "ws1", "ssh ws1 works, with no user name and no password (challenge)"
    broke = (lab.STATE / "6.2-broken").exists()
    code, out = lab.ssh("srv1", "hostname")
    yield (code == 0 and out.strip() == "srv1", "ssh srv1 works too (challenge)"
           + ("" if code == 0 else ": " + (out.splitlines()[-1][:120] if out else "no answer")))
    code, out = lab.sh("srv1", "cat /home/netops/handover.txt 2>/dev/null")
    same = code == 0 and out.strip() == (ROOT / "files" / "notes" / "handover.txt").read_text().strip()
    yield same, "files/notes/handover.txt is on srv1, in netops's home folder (challenge)"
    yield (broke, "make break T=6.2 rebuilt srv1, and you fixed known_hosts (challenge)"
           + ("" if broke else ": run make break T=6.2, then get ssh srv1 working again"))


# ── chapter 7 · a little Bash scripting ───────────────────────────────────────
def script(name, *args, cwd=None):
    p = ROOT / "scripts" / name
    if not mode(p) & 0o100:
        return None, f"scripts/{name} isn't executable yet: chmod +x scripts/{name}"
    try:
        p = lab.subprocess.run([str(p), *args], capture_output=True, text=True, timeout=60, cwd=cwd or ROOT,
                               env=lab.fresh_env())
        return p, ""
    except PermissionError:
        return None, f"scripts/{name} isn't executable yet: chmod +x scripts/{name}"
    except OSError as e:
        return None, f"it won't start ({e.strerror}): is the first line #!/usr/bin/env bash?"
    except lab.subprocess.TimeoutExpired:
        return None, "it didn't finish within a minute"


def t7_1():
    need("ws1", "srv1", "r1")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lcli-hosts-"))
    cases = [
        ("hosts.txt", None, {"ws1": "up", "srv1": "up", "r1": "up", "172.80.102.99": "down"}, 1),
        ("up.txt", "# all of these answer\nws1\n\nr1\n", {"ws1": "up", "r1": "up"}, 0),
        ("mixed.txt", "srv1\n172.80.102.98\n# a comment\nws1\n", {"srv1": "up", "172.80.102.98": "down", "ws1": "up"}, 1),
    ]
    for name, text, want, code in cases:
        args = []
        if text is not None:
            (tmp / name).write_text(text)
            args = [str(tmp / name)]
        p, why = script("reach.sh", *args)
        label = f"reach.sh on {'hosts.txt (no argument)' if not args else 'a list it hadn’t seen'}"
        if p is None:
            yield False, f"{label}: {why}"
            return
        got = dict(tuple(line.split()[:2]) for line in p.stdout.splitlines() if len(line.split()) >= 2)
        lines_ok = got == want and len(p.stdout.splitlines()) == len(want)
        yield (lines_ok and p.returncode == code,
               f"{label}: one 'name up|down' line per host, exit code {code} (follow along)"
               + ("" if lines_ok else f": it printed {p.stdout.strip()[:80]!r}") + ("" if p.returncode == code else f", exit code {p.returncode}"))


def cfg_text(host, ntp):
    return (f"hostname {host}\n!\ninterface GigabitEthernet1\n ip address 10.0.0.1 255.255.255.0\n!\n"
            + ("ntp server 192.168.20.10\n!\n" if ntp else "") + "end\n")


def t7_2():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lcli-audit-"))
    sets = {
        "the practice folder files/configs": (ROOT / "files" / "configs", ["chi leaf2.cfg", "nyc-leaf2.cfg"], 1),
        "a folder where every config has NTP": ({"a.cfg": True, "b c.cfg": True, "notes.txt": False}, [], 0),
        "a folder it hadn't seen": ({"edge one.cfg": False, "edge2.cfg": True, "core.cfg": False, "x.txt": False},
                                    ["core.cfg", "edge one.cfg"], 1),
        "an empty folder": ({}, [], 0),
    }
    for label, (spec, want, code) in sets.items():
        if isinstance(spec, dict):
            d = tmp / str(abs(hash(label)))
            d.mkdir()
            for name, ntp in spec.items():
                (d / name).write_text(cfg_text(name.split(".")[0].replace(" ", "-"), ntp))
        else:
            d = spec
        p, why = script("audit.sh", str(d))
        if p is None:
            yield False, f"audit.sh on {label}: {why}"
            return
        got = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
        names = [os.path.basename(g) for g in got]
        ok = sorted(names) == sorted(want) and p.returncode == code
        yield (ok, f"audit.sh on {label}: lists {', '.join(want) or 'nothing'}, exit code {code} (challenge)"
               + ("" if ok else f": it listed {', '.join(names) or 'nothing'}, exit code {p.returncode}"))
    p, why = script("audit.sh")
    if p is not None:
        ok = p.returncode == 2 and not p.stdout.strip() and p.stderr.strip()
        yield (ok, "audit.sh with no folder: a usage line on stderr, exit code 2 (challenge)"
               + ("" if ok else f": exit code {p.returncode}{', and it printed to stdout' if p.stdout.strip() else ''}"
                  f"{'' if p.stderr.strip() else ', nothing on stderr'}"))


# ── chapter 8 · the network from the command line ─────────────────────────────
def ws1(cmd):
    return lab.sh("ws1", cmd, user="netops", timeout=30)


def t8_1():
    need("ws1", "r1", "srv1")
    doc = answers("8.1")
    code, out = ws1("ip -4 route show default")
    gw = out.split()[2] if out.startswith("default via") else None
    yield ask(doc, "gateway", gw, "ws1's default gateway (follow along)", low)
    code, out = ws1("ip -o -4 addr show")
    mgmt = next((w.split()[1] for w in out.splitlines() if " 172.80.102." in w), None)
    yield ask(doc, "mgmt_interface", mgmt, "the interface on the management network (follow along)", low)
    yield ask(doc, "srv1_address", "192.168.20.10", "srv1's address, from dig (follow along)", low)
    yield ask(doc, "dns_server", "192.168.20.10", "ws1's DNS server (follow along)", low,
              "but that's not what /etc/resolv.conf on ws1 says.")
    # ws1 → r1 → srv1 is fixed by the topology. (Counting live would trip on traceroute's stars: Linux
    # rate-limits the ICMP errors traceroute relies on, so a second run straight after the first can miss them.)
    yield ask(doc, "hops_to_srv1", 2, "how many hops traceroute counts to srv1 (challenge)", low,
              "but traceroute -n srv1 lists a different number of lines. If it shows stars, wait a few seconds and run it again.")
    yield ask(doc, "route_dev", "eth1", "the interface ws1 sends srv1's packets out of (challenge)", low,
              "but that's not what ip route get 192.168.20.10 says after dev.")


def t8_2():
    need("ws1", "srv1")
    doc = answers("8.2")
    yield ask(doc, "listen_before", "127.0.0.1", "where labweb listened at first (challenge)", lambda s: low(s).split(":")[0],
              "but that's not what ss -tlnp on srv1 showed before you changed anything.")
    yield ask(doc, "curl_said", "refused", "the word curl -v used for the failure (challenge)",
              lambda s: "refused" if "refused" in low(s) else low(s))
    code, out = lab.sh("srv1", "ss -Htln 'sport = :8080'")
    addr = out.split()[3].rsplit(":", 1)[0] if out.split() else ""
    yield ask(doc, "listen_after", {addr} if addr not in ("", "127.0.0.1") else set(),
              "where labweb listens now (challenge)", lambda s: low(s).split(":")[0] if low(s) != "*" else "0.0.0.0",
              "but ss on srv1 says something else, or it still listens only on 127.0.0.1")
    code, out = ws1("curl -s -m 3 -o /dev/null -w '%{http_code}' http://srv1:8080/")
    yield out.strip() == "200", f"curl http://srv1:8080 from ws1 gets the page (challenge): {out.strip() or 'no answer'}"


def t8_3():
    need("ws1")
    doc = answers("8.3")
    pcap = ROOT / "captures" / "web.pcap"
    code, out = ws1("test -s web.pcap")
    yield code == 0, "ws1 has web.pcap in netops's home folder (follow along)"
    if not pcap.exists():
        yield False, "captures/web.pcap is in the lab's folder, copied back with scp (follow along)"
        return
    yield True, "captures/web.pcap is in the lab's folder, copied back with scp (follow along)"
    code, out = lab.run(["tcpdump", "-n", "-r", str(pcap)], 20)
    pkts = [ln for ln in out.splitlines() if re.match(r"\d\d:\d\d:\d\d", ln)]
    syn = next((ln for ln in pkts if "Flags [S]," in ln and "> 192.168.20.10.8080" in ln), None)
    yield bool(syn), "it holds a connection to srv1 port 8080, from its first SYN (follow along)"
    if not syn:
        return
    port = syn.split()[2].rsplit(".", 1)[1]
    yield ask(doc, "client_port", port, "ws1's own port for the connection (challenge)", low,
              "but the SYN in the capture came from a different port.")
    yield ask(doc, "packets", len(pkts), "how many packets the capture holds (challenge)", low)
    code, text = lab.run(["tcpdump", "-n", "-A", "-r", str(pcap)], 20)
    yield ("GET / HTTP" in text, "and the HTTP request, GET /, is in it (challenge)")


# ── the tasks ──────────────────────────────────────────────────────────────────
TASKS = {
    "1.1": "where am I?", "1.2": "paths",
    "2.1": "read and write", "2.2": "tidy up",
    "3.1": "pipelines", "3.2": "who's knocking?",
    "4.1": "who may do what", "4.2": "too open, too closed",
    "5.1": "jobs and variables", "5.2": "runaway",
    "6.1": "your first key", "6.2": "short names, a copy, a changed key",
    "7.1": "is everyone up?", "7.2": "audit the configs",
    "8.1": "where does it go?", "8.2": "refused", "8.3": "catch it on the wire",
}
CHAPTERS = {1: "the shell and the filesystem", 2: "working with files", 3: "pipes, redirection and grep",
            4: "users, permissions and sudo", 5: "processes, environment variables and PATH", 6: "SSH and keys",
            7: "a little Bash scripting", 8: "the network from the command line"}


def report(t):
    print(f"{C['c']}╭─{C['x']} {C['b']}task {t}{C['x']} {C['d']}·{C['x']} {TASKS[t]}", flush=True)
    results = []
    try:
        for ok, msg in globals()[f"t{t.replace('.', '_')}"]():
            ok = bool(ok)
            results.append(ok)
            print(f"{C['c']}│{C['x']}  {C['g'] + '✓' if ok else C['r'] + '✗'}{C['x']} {msg}", flush=True)
    except Exception as e:  # a half-finished task shouldn't crash the checker
        results.append(False)
        print(f"{C['c']}│{C['x']}  {C['r']}✗{C['x']} {str(e).splitlines()[0][:160] if str(e) else type(e).__name__}")
    passed = sum(results)
    done = passed == len(results)
    tail = (f"{C['g']}verified{C['x']}" if done else
            f"{C['y']}stuck?{C['x']} the hints and the answer are on the guide page  "
            f"{C['d']}{GUIDE}/task-{t.replace('.', '-')}/{C['x']}")
    print(f"{C['c']}╰─{C['x']} {passed}/{len(results)} checks passed  {tail}\n")
    return done


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg.startswith("ch"):
        n = int(arg[2:])
        print(f"{C['b']}chapter {n} · {CHAPTERS.get(n, '')}{C['x']}\n")
        sys.exit(0 if all([report(t) for t in TASKS if t.startswith(f"{n}.")]) else 1)
    if arg == "all":
        done = [t for t in TASKS if report(t)]
        print(f"{C['b']}{len(done)}/{len(TASKS)} tasks verified{C['x']}")
        sys.exit(0 if len(done) == len(TASKS) else 1)
    if arg not in TASKS:
        sys.exit(f"no task {arg}: tasks are {', '.join(TASKS)}")
    sys.exit(0 if report(arg) else 1)
