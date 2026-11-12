# Linux and the command line 101

**[▶ Open the lab](https://labs.networkdoodles.com/open/linux-cli-101)**: one click, nothing to install

The hands-on lab for [Linux and the command line 101](https://networkdoodles.com/lessons/linux-cli-101/): the
shell and the filesystem, files, pipes and grep, permissions, processes and PATH, SSH and keys, a little Bash,
and the network commands, on a real Linux machine with a small network next to it.

**The guide:** https://networkdoodles.com/labs/linux-cli-101/

```
  codespace ─ ─ management network 172.80.102.0/24 ─ ─ ws1, srv1, r1

  ws1 ──────── r1 ──────── srv1
  192.168.10.10   192.168.10.1 · 192.168.20.1   192.168.20.10
```

## Start

**Open the lab** (the link above, or the button on the [guide's page](https://networkdoodles.com/labs/linux-cli-101/)) and
sign in with GitHub. It creates your own codespace, on your GitHub account's free allowance, and opens the lab
app: the guide on the left, VS Code on the right. The first start takes a few minutes; the top bar says
**network up** when it's ready. Then follow [task 1.1](https://networkdoodles.com/labs/linux-cli-101/task-1-1/):
**Check task**, under the guide, checks your work.

On your own laptop instead: open the repo in its dev container (VS Code's *Reopen in Container*, or
`npx @devcontainers/cli up --workspace-folder .`), then the lab app is at http://localhost:8000.

## Commands

| Command | What it does |
|---|---|
| `make check T=1.1` | check a task (`CH=1` checks a chapter, nothing checks them all) |
| `make status` | what's running |
| `make live` | task 2.1: a minute of new lines in `files/logs/live.log` |
| `make break T=4.2` | set up a task's problem (tasks 4.2, 5.2 and 6.2) |
| `make solve T=1.2` | stuck, or skipped a task? does it for you and fills in its answers, printing every command |
| `make reset` | put the network back how it started. Your files, `~/.ssh` and `~/.bashrc` stay as they are |
| `make shell H=ws1` | a root shell on a machine, without SSH (for when you've locked yourself out) |
| `make help` | everything else |

The codespace is Debian 12. ws1 and srv1 are Debian 13 machines with OpenSSH; their user is `netops`, password
`netops-lab`. r1 runs CapeOS Bolt, a lab network OS with an IOS-style CLI: user `admin`, password `capeos-lab`.
These are lab-only passwords for machines that exist only inside your codespace.
